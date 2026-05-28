"""Merge action — merges PR when all conditions are met."""

from __future__ import annotations

import logging

from agentic_devtools.cli.ci.guards import LABEL_AUTO_MERGE_ALLOWED
from agentic_devtools.cli.ci.pipeline.models import ActionDecision, ActionResult
from agentic_devtools.cli.ci.pipeline.snapshot import (
    DerivedState,
    PRStateSnapshot,
    has_non_copilot_changes_requested_on_head,
)
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)


def _build_squash_commit_message(snapshot: PRStateSnapshot) -> str:
    """Build a descriptive commit message for squash merges.

    Uses the PR title as the commit subject line with the PR number appended.
    """
    if snapshot.title:
        return f"{snapshot.title} (#{snapshot.pr_number})"
    return f"PR #{snapshot.pr_number}"


def _is_review_clean(snapshot: PRStateSnapshot) -> bool:
    """Return True if the Copilot review on HEAD is clean (not actionable).

    Clean means: APPROVED, or COMMENTED with 0 inline comments.
    """
    if snapshot.review_state == "APPROVED":
        return True
    if snapshot.review_state == "COMMENTED" and snapshot.copilot_review_inline_count == 0:
        return True
    return False


class MergeAction:
    """Merge the PR when fully ready.

    Preconditions:
    - Approved (on HEAD)
    - CI passing
    - `ai-auto-merge-allowed` label present
    - PR is mergeable
    - No unresolved threads
    - No pending Copilot review
    - No effective non-Copilot CHANGES_REQUESTED review on HEAD
    - Copilot review on HEAD exists and is non-actionable (clean)

    Idempotency: Already merged → skip (PR state).
    """

    @property
    def name(self) -> str:
        return "merge"

    def evaluate(self, snapshot: PRStateSnapshot, derived: DerivedState) -> ActionResult:
        """Evaluate whether the PR can be merged."""
        preconditions: dict[str, bool] = {}

        # Not a draft — use derived so PublishAction's same-run effect is visible
        is_not_draft = not derived.is_draft
        preconditions["not_draft"] = is_not_draft
        if not is_not_draft:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="PR is a draft",
            )

        # Must be approved
        has_approval = derived.has_approval_on_head
        preconditions["approved"] = has_approval
        if not has_approval:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="PR not approved on HEAD",
            )

        # CI passing
        preconditions["ci_passing"] = snapshot.ci_status == "passing"
        if snapshot.ci_status != "passing":
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details=f"CI is {snapshot.ci_status}",
            )

        # Auto-merge label
        has_label = LABEL_AUTO_MERGE_ALLOWED in snapshot.labels
        preconditions["has_auto_merge_label"] = has_label
        if not has_label:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="Missing 'ai-auto-merge-allowed' label",
            )

        # Mergeable
        is_mergeable = snapshot.mergeable is not False  # None treated as potentially mergeable
        preconditions["mergeable"] = is_mergeable
        if not is_mergeable:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="PR is not mergeable",
            )

        # No unresolved threads — consult derived state so same-run ResolveThreadsAction
        # effects are visible (avoids a second workflow trigger after thread resolution).
        unresolved = derived.unresolved_threads
        preconditions["no_unresolved_threads"] = unresolved == 0
        if unresolved > 0:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details=f"{unresolved} unresolved thread(s)",
            )

        # No pending Copilot review (check derived in case request_review just ran)
        has_pending_review = derived.copilot_review_pending
        preconditions["no_pending_review"] = not has_pending_review
        if has_pending_review:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="Copilot review is pending",
            )

        # No non-Copilot CHANGES_REQUESTED on HEAD
        has_human_changes_requested = has_non_copilot_changes_requested_on_head(snapshot.reviews, snapshot.head_sha)
        preconditions["no_human_changes_requested"] = not has_human_changes_requested
        if has_human_changes_requested:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="Non-Copilot reviewer requested changes on current HEAD",
            )

        # Copilot review must exist on HEAD
        has_copilot_review = snapshot.copilot_review_id > 0 and bool(snapshot.review_state)
        preconditions["has_copilot_review"] = has_copilot_review
        if not has_copilot_review:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="No Copilot review on HEAD",
            )

        # Copilot review must be clean (non-actionable)
        review_clean = _is_review_clean(snapshot)
        preconditions["review_clean"] = review_clean
        if not review_clean:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details=(
                    f"Copilot review is actionable "
                    f"(state={snapshot.review_state}, inline={snapshot.copilot_review_inline_count})"
                ),
            )

        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            preconditions=preconditions,
            details="All merge conditions met",
        )

    def execute(
        self,
        provider: CIPlatformProvider,
        snapshot: PRStateSnapshot,
        derived: DerivedState,
    ) -> ActionResult:
        """Execute the merge."""
        # Use squash merge for multi-commit PRs to maintain clean history
        commit_count = getattr(derived, "commit_count", snapshot.commit_count)
        if commit_count > 1:
            method = "squash"
            commit_message = _build_squash_commit_message(snapshot)
        else:
            method = "rebase"
            commit_message = None

        try:
            if method == "squash" and commit_message:
                provider.merge_pr(snapshot.pr_number, snapshot.head_sha, method, commit_message=commit_message)
            else:
                provider.merge_pr(snapshot.pr_number, snapshot.head_sha, method)
        except Exception as exc:
            logger.error("PR #%d: Merge failed: %s", snapshot.pr_number, exc)
            return ActionResult(
                name=self.name,
                decision=ActionDecision.FAILED,
                error=str(exc),
                details="merge_pr call failed",
            )

        logger.info("PR #%d: Merged successfully (method=%s)", snapshot.pr_number, method)
        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            details=f"PR merged via {method}",
        )
