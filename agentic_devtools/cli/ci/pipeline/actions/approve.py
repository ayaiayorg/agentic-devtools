"""Approve action — auto-approves PR when conditions are met."""

from __future__ import annotations

import logging

from agentic_devtools.cli.ci.pipeline.models import ActionDecision, ActionResult
from agentic_devtools.cli.ci.pipeline.snapshot import (
    DerivedState,
    PRStateSnapshot,
    has_non_copilot_changes_requested_on_head,
)
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)


def _is_review_clean(snapshot: PRStateSnapshot) -> bool:
    """Return True if the Copilot review on HEAD is clean (not actionable).

    Clean means: APPROVED, or COMMENTED with 0 inline comments.
    """
    if snapshot.review_state == "APPROVED":
        return True
    if snapshot.review_state == "COMMENTED" and snapshot.copilot_review_inline_count == 0:
        return True
    return False


class ApproveAction:
    """Approve the PR when all conditions are met.

    Preconditions:
    - No existing approval on current HEAD SHA
    - No effective non-Copilot CHANGES_REQUESTED review on HEAD
    - Copilot review is clean on HEAD
    - CI passing
    - No unresolved threads

    Idempotency: Already approved on HEAD → skip.
    """

    @property
    def name(self) -> str:
        return "approve"

    def evaluate(self, snapshot: PRStateSnapshot, derived: DerivedState) -> ActionResult:
        """Evaluate whether approval should be submitted."""
        preconditions: dict[str, bool] = {}

        # No existing approval on HEAD
        preconditions["no_approval_on_head"] = not snapshot.has_approval_on_head
        if snapshot.has_approval_on_head:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="Already approved on current HEAD",
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

        # CI passing
        preconditions["ci_passing"] = snapshot.ci_status == "passing"
        if snapshot.ci_status != "passing":
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details=f"CI is {snapshot.ci_status}",
            )

        # Clean Copilot review
        review_clean = _is_review_clean(snapshot)
        preconditions["review_clean"] = review_clean
        if not review_clean:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details=(
                    f"Copilot review is not clean "
                    f"(state={snapshot.review_state}, inline={snapshot.copilot_review_inline_count})"
                ),
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

        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            preconditions=preconditions,
            details="All conditions met for approval",
        )

    def execute(
        self,
        provider: CIPlatformProvider,
        snapshot: PRStateSnapshot,
        derived: DerivedState,
    ) -> ActionResult:
        """Submit PR approval."""
        try:
            approved = provider.approve_pr(
                snapshot.pr_number,
                snapshot.head_sha,
                "Auto-approved by AI PR loop",
            )
        except Exception as exc:
            logger.error("PR #%d: Approval failed: %s", snapshot.pr_number, exc)
            return ActionResult(
                name=self.name,
                decision=ActionDecision.FAILED,
                error=str(exc),
                details="approve_pr call failed",
            )

        if not approved:
            logger.warning("PR #%d: Approval was skipped by provider", snapshot.pr_number)
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions={"approver_token_available": False},
                details="Provider skipped approval (missing approver token?)",
            )

        logger.info("PR #%d: Approved", snapshot.pr_number)
        derived.set("has_approval_on_head", True)

        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            details="PR approved",
        )
