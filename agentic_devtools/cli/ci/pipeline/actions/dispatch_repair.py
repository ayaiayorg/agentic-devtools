"""Dispatch repair action — triggers AI repair on CI failure or actionable review."""

from __future__ import annotations

import logging

from agentic_devtools.cli.ci.guards import check_cycle_limit, check_deduplication
from agentic_devtools.cli.ci.pipeline.models import ActionDecision, ActionResult
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)


def _is_copilot_review_actionable(snapshot: PRStateSnapshot) -> bool:
    """Return True if the Copilot review on HEAD is actionable.

    Actionable means CHANGES_REQUESTED, or COMMENTED with inline comments.
    Unknown inline counts fail closed and are treated as actionable.
    """
    if snapshot.review_state == "CHANGES_REQUESTED" and snapshot.copilot_review_id > 0:
        return True
    if (
        snapshot.review_state == "COMMENTED"
        and snapshot.copilot_review_id > 0
        and snapshot.copilot_review_inline_count != 0
    ):
        return True
    return False


class DispatchRepairAction:
    """Dispatch a repair when CI fails or actionable Copilot review exists.

    Preconditions:
    - CI failed OR actionable Copilot review on HEAD
    - Deduplication limit not exceeded
    - Cycle limit not exceeded

    Idempotency: Recent dispatch → skip.
    """

    @property
    def name(self) -> str:
        return "dispatch_repair"

    def evaluate(self, snapshot: PRStateSnapshot, derived: DerivedState) -> ActionResult:
        """Evaluate whether repair dispatch is needed."""
        preconditions: dict[str, bool] = {}

        # CI failed OR actionable review
        ci_failing = snapshot.ci_status == "failing"
        review_actionable = _is_copilot_review_actionable(snapshot)
        needs_repair = ci_failing or review_actionable
        preconditions["ci_failing"] = ci_failing
        preconditions["review_actionable"] = review_actionable
        preconditions["needs_repair"] = needs_repair
        if not needs_repair:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details=f"No repair needed (ci_status={snapshot.ci_status}, review_actionable={review_actionable})",
            )

        # CI pending check - don't dispatch repair while CI still running
        if snapshot.ci_status == "pending":
            preconditions["ci_not_pending"] = False
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="CI still pending — waiting",
            )
        preconditions["ci_not_pending"] = True

        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            preconditions=preconditions,
            details=f"Repair needed (ci_failing={ci_failing}, review_actionable={review_actionable})",
        )

    def execute(
        self,
        provider: CIPlatformProvider,
        snapshot: PRStateSnapshot,
        derived: DerivedState,
    ) -> ActionResult:
        """Dispatch repair by posting @copilot comment."""
        # Check deduplication limits
        try:
            dedup_skip, dedup_count = check_deduplication(provider, snapshot.pr_number, snapshot.head_sha)
        except Exception as exc:
            logger.warning("PR #%d: Dedup check failed: %s", snapshot.pr_number, exc)
            return ActionResult(
                name=self.name,
                decision=ActionDecision.FAILED,
                error=str(exc),
                details="Deduplication check failed",
            )

        if dedup_skip:
            logger.info(
                "PR #%d: Dedup limit reached (count=%d, sha=%s)",
                snapshot.pr_number,
                dedup_count,
                snapshot.head_sha[:8],
            )
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                details=f"Dedup limit reached (count={dedup_count})",
                limit_reached=True,
            )

        # Check cycle limit
        try:
            cycle_reached, cycle_count = check_cycle_limit(provider, snapshot.pr_number)
        except Exception as exc:
            logger.warning("PR #%d: Cycle limit check failed: %s", snapshot.pr_number, exc)
            return ActionResult(
                name=self.name,
                decision=ActionDecision.FAILED,
                error=str(exc),
                details="Cycle limit check failed",
            )

        if cycle_reached:
            logger.info("PR #%d: Cycle limit reached (count=%d)", snapshot.pr_number, cycle_count)
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                details=f"Cycle limit reached (count={cycle_count})",
                limit_reached=True,
            )

        # Determine repair type
        ci_failing = snapshot.ci_status == "failing"
        review_actionable = _is_copilot_review_actionable(snapshot)

        if ci_failing and review_actionable:
            repair_type = "both"
        elif review_actionable:
            repair_type = "review"
        else:
            repair_type = "ci"

        # Get actionable failed checks for context (same subset used by ci_status gating)
        actionable_failed_check_names = set(snapshot.ci_failed_checks)
        failed_checks = [cr for cr in snapshot.check_runs if cr.name in actionable_failed_check_names]

        # Get review comments if needed
        review_comments = []
        if review_actionable and snapshot.copilot_review_id:
            try:
                review_comments = provider.list_review_comments(snapshot.pr_number, snapshot.copilot_review_id)
            except Exception as exc:
                logger.warning("PR #%d: Failed to fetch review comments: %s", snapshot.pr_number, exc)

        # Dispatch the repair
        try:
            comment_id = provider.dispatch_repair(
                pr_number=snapshot.pr_number,
                head_sha=snapshot.head_sha,
                repair_type=repair_type,
                failed_checks=failed_checks,
                review_comments=review_comments,
                review_id=snapshot.copilot_review_id,
            )
        except Exception as exc:
            logger.error("PR #%d: Repair dispatch failed: %s", snapshot.pr_number, exc)
            return ActionResult(
                name=self.name,
                decision=ActionDecision.FAILED,
                error=str(exc),
                details="dispatch_repair call failed",
            )

        logger.info(
            "PR #%d: Repair dispatched (type=%s, comment_id=%d)",
            snapshot.pr_number,
            repair_type,
            comment_id,
        )

        derived.set("repair_dispatched", True)

        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            details=f"Repair dispatched (type={repair_type}, comment_id={comment_id})",
        )
