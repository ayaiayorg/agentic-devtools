"""Publish action — publishes draft PRs."""

from __future__ import annotations

import logging

from agentic_devtools.cli.ci.pipeline.models import ActionDecision, ActionResult
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)


def _is_wip_title(title: str) -> bool:
    """Return True when a PR title is explicitly marked work-in-progress."""
    return title.upper().startswith("[WIP]")


class PublishAction:
    """Publish a draft PR when it has changes and is not WIP.

    Preconditions:
    - PR is draft
    - PR has file changes
    - PR title is not WIP

    Idempotency: Already published → skip.
    """

    @property
    def name(self) -> str:
        return "publish"

    def evaluate(self, snapshot: PRStateSnapshot, derived: DerivedState) -> ActionResult:
        """Evaluate whether the PR should be published."""
        preconditions: dict[str, bool] = {}

        is_draft = derived.is_draft
        preconditions["is_draft"] = is_draft
        if not is_draft:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="PR is not a draft",
            )

        has_changes = derived.has_changes
        preconditions["has_changes"] = has_changes
        if not has_changes:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="PR has no file changes",
            )

        is_wip = _is_wip_title(snapshot.title)
        preconditions["not_wip"] = not is_wip
        if is_wip:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="PR title is WIP",
            )

        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            preconditions=preconditions,
            details="Draft PR ready to publish",
        )

    def execute(
        self,
        provider: CIPlatformProvider,
        snapshot: PRStateSnapshot,
        derived: DerivedState,
    ) -> ActionResult:
        """Squash before publish + publish the PR."""
        # Squash before publish
        try:
            provider.squash_before_publish(
                pr_number=snapshot.pr_number,
                base_branch=snapshot.base_branch,
                head_branch=snapshot.head_branch,
                head_sha=snapshot.head_sha,
            )
        except Exception as exc:
            logger.error("PR #%d: squash_before_publish failed: %s", snapshot.pr_number, exc)
            return ActionResult(
                name=self.name,
                decision=ActionDecision.FAILED,
                error=str(exc),
                details="squash_before_publish failed",
            )

        # Publish
        try:
            provider.publish_pr(snapshot.pr_number)
        except Exception as exc:
            logger.error("PR #%d: publish_pr failed: %s", snapshot.pr_number, exc)
            return ActionResult(
                name=self.name,
                decision=ActionDecision.FAILED,
                error=str(exc),
                details="publish_pr failed",
            )

        # Update derived state
        derived.set("is_draft", False)
        logger.info("PR #%d: Published (draft → ready)", snapshot.pr_number)

        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            details="Published draft PR",
            invalidates_snapshot=True,
        )
