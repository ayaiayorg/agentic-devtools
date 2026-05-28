"""Squash action — squashes commits when multiple exist."""

from __future__ import annotations

import logging

from agentic_devtools.cli.ci.pipeline.models import ActionDecision, ActionResult
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)


class SquashAction:
    """Squash commits when more than one exists above merge-base.

    Preconditions:
    - Commits above merge-base > 1
    - No active Copilot session (coding or review)
    - CI passing

    Idempotency: Already 1 commit → skip.
    """

    @property
    def name(self) -> str:
        return "squash"

    def evaluate(self, snapshot: PRStateSnapshot, derived: DerivedState) -> ActionResult:
        """Evaluate whether squash is needed."""
        preconditions: dict[str, bool] = {}

        # Must have more than 1 commit
        preconditions["commits_gt_1"] = snapshot.commit_count > 1
        if snapshot.commit_count <= 1:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details=f"Only {snapshot.commit_count} commit(s) — nothing to squash",
            )

        # Repair dispatch in this run should keep HEAD stable for the repair cycle.
        repair_dispatched = getattr(derived, "repair_dispatched", False)
        preconditions["no_repair_dispatched"] = not repair_dispatched
        if repair_dispatched:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="Repair dispatched — deferring squash",
            )

        # No active Copilot session (coding/repair only — pending review does NOT block squash)
        preconditions["no_active_session"] = not snapshot.active_session
        if snapshot.active_session:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="Copilot session active — deferring squash",
            )

        # CI must be passing
        preconditions["ci_passing"] = snapshot.ci_status == "passing"
        if snapshot.ci_status != "passing":
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details=f"CI is {snapshot.ci_status} — deferring squash",
            )

        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            preconditions=preconditions,
            details=f"{snapshot.commit_count} commits to squash",
        )

    def execute(
        self,
        provider: CIPlatformProvider,
        snapshot: PRStateSnapshot,
        derived: DerivedState,
    ) -> ActionResult:
        """Execute the squash operation."""
        try:
            provider.squash_post_repair(
                pr_number=snapshot.pr_number,
                base_branch=snapshot.base_branch,
                head_branch=snapshot.head_branch,
                head_sha=snapshot.head_sha,
            )
        except Exception as exc:
            logger.error("PR #%d: Squash failed: %s", snapshot.pr_number, exc)
            return ActionResult(
                name=self.name,
                decision=ActionDecision.FAILED,
                error=str(exc),
                details="squash_post_repair failed",
            )

        logger.info("PR #%d: Squashed commits", snapshot.pr_number)
        derived.set("commit_count", 1)

        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            details=f"Squashed {snapshot.commit_count} commits into 1",
            invalidates_snapshot=True,
        )
