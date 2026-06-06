"""Dispatch repair action — triggers AI repair on CI failure or actionable review."""

from __future__ import annotations

import logging

from agentic_devtools.cli.ci.guards import (
    check_cycle_limit,
    check_deduplication,
    is_duplicate_trigger,
)
from agentic_devtools.cli.ci.models import COPILOT_LOGINS, ReviewInfo
from agentic_devtools.cli.ci.pipeline.exclusion import ExclusionContext
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


def _list_prior_actionable_copilot_reviews(snapshot: PRStateSnapshot) -> list[ReviewInfo]:
    """Return actionable Copilot reviews that target commits prior to HEAD."""
    return [
        r
        for r in snapshot.reviews
        if r.user in COPILOT_LOGINS
        and r.commit_sha
        and r.commit_sha != snapshot.head_sha
        and r.state in ("CHANGES_REQUESTED", "COMMENTED")
    ]


def _has_stuck_prior_review_threads(snapshot: PRStateSnapshot) -> bool:
    """Return True when unresolved prior-review threads should trigger repair."""
    return (
        snapshot.ci_status == "passing"
        and snapshot.copilot_review_id == 0
        and snapshot.unresolved_threads > 0
        and bool(_list_prior_actionable_copilot_reviews(snapshot))
    )


class DispatchRepairAction:
    """Dispatch a repair when CI fails or actionable review feedback exists.

    Preconditions:
    - CI failed OR actionable Copilot review on HEAD
      OR stuck unresolved threads from prior Copilot review(s)
    - Deduplication limit not exceeded
    - Cycle limit not exceeded

    Idempotency: Recent dispatch → skip.
    """

    runs_after_invalidation = True

    @property
    def name(self) -> str:
        return "dispatch_repair"

    def evaluate(self, snapshot: PRStateSnapshot, derived: DerivedState) -> ActionResult:
        """Evaluate whether repair dispatch is needed."""
        preconditions: dict[str, bool] = {}

        # CI failed OR actionable review OR unresolved prior-review threads are stuck
        ci_failing = snapshot.ci_status == "failing"
        review_actionable = _is_copilot_review_actionable(snapshot)
        stuck_prior_threads = _has_stuck_prior_review_threads(snapshot)
        needs_repair = ci_failing or review_actionable or stuck_prior_threads
        preconditions["ci_failing"] = ci_failing
        preconditions["review_actionable"] = review_actionable
        preconditions["stuck_prior_threads"] = stuck_prior_threads
        preconditions["needs_repair"] = needs_repair
        if not needs_repair:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details=(
                    "No repair needed "
                    f"(ci_status={snapshot.ci_status}, review_actionable={review_actionable}, "
                    f"stuck_prior_threads={stuck_prior_threads})"
                ),
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
        # Check review-ID level deduplication first (FR-012).
        # Applies to both normal actionable reviews on HEAD and stuck prior-review
        # thread repairs (where review context is from a prior commit review).
        review_actionable = _is_copilot_review_actionable(snapshot)
        prior_reviews = _list_prior_actionable_copilot_reviews(snapshot)
        prior_reviews.sort(
            key=lambda r: (
                r.submitted_at if isinstance(r.submitted_at, str) else "",
                r.id,
            ),
            reverse=True,
        )
        stuck_prior_threads = _has_stuck_prior_review_threads(snapshot)
        review_context_id = (
            snapshot.copilot_review_id if review_actionable else (prior_reviews[0].id if stuck_prior_threads else 0)
        )
        if review_context_id > 0:
            try:
                if is_duplicate_trigger(provider, snapshot.pr_number, review_context_id):
                    logger.info(
                        "PR #%d: Trigger comment already exists for review_id=%d — skipping",
                        snapshot.pr_number,
                        review_context_id,
                    )
                    return ActionResult(
                        name=self.name,
                        decision=ActionDecision.SKIP,
                        details=f"Repair already dispatched for review_id={review_context_id}",
                    )
            except Exception as exc:
                logger.warning("PR #%d: Review-ID dedup check failed: %s", snapshot.pr_number, exc)
                # Fail-open: proceed with dispatch on transient API failures; the
                # review-ID dedup guard is best-effort and should not block repair.

        ci_failing = snapshot.ci_status == "failing"
        ci_passing = snapshot.ci_status == "passing"
        dedup_kwargs = {"max_dispatches": 1} if ci_failing and not (review_actionable or stuck_prior_threads) else {}

        # Check deduplication limits
        try:
            dedup_skip, dedup_count = check_deduplication(
                provider,
                snapshot.pr_number,
                snapshot.head_sha,
                **dedup_kwargs,
            )
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
        review_repair_needed = review_actionable or stuck_prior_threads
        if ci_failing and review_repair_needed:
            repair_type = "both"
        elif review_repair_needed:
            repair_type = "review"
        else:
            repair_type = "ci"

        # Get actionable failed checks for context (same subset used by ci_status gating)
        actionable_failed_check_names = set(snapshot.ci_failed_checks)
        failed_checks = [cr for cr in snapshot.check_runs if cr.name in actionable_failed_check_names]

        # Get review comments if needed
        review_comments = []
        if review_repair_needed and review_context_id:
            review_ids = [r.id for r in prior_reviews] if stuck_prior_threads else [review_context_id]
            seen_comment_keys: set[tuple[int, int]] = set()
            for review_id in review_ids:
                try:
                    for comment in provider.list_review_comments(snapshot.pr_number, review_id):
                        dedup_key = (review_id, comment.id) if comment.id < 0 else (0, comment.id)
                        if dedup_key in seen_comment_keys:
                            continue
                        seen_comment_keys.add(dedup_key)
                        review_comments.append(comment)
                except Exception as exc:
                    logger.warning("PR #%d: Failed to fetch review comments: %s", snapshot.pr_number, exc)

        # Filter out comments already handled by ApplySuggestionsAction (FR-005, FR-006)
        exclusion_ctx: ExclusionContext | None = derived.get("exclusion_context")
        if exclusion_ctx and exclusion_ctx.resolved_comment_ids and review_comments:
            original_count = len(review_comments)
            review_comments = [rc for rc in review_comments if rc.id not in exclusion_ctx.resolved_comment_ids]
            filtered_count = original_count - len(review_comments)
            if filtered_count > 0:
                logger.info(
                    "PR #%d: Excluded %d review comments already auto-applied",
                    snapshot.pr_number,
                    filtered_count,
                )

            # Re-evaluate: if no review comments remain and CI is passing, skip repair
            if not review_comments and ci_passing:
                logger.info(
                    "PR #%d: All review comments were auto-applied and CI is passing — skipping repair",
                    snapshot.pr_number,
                )
                return ActionResult(
                    name=self.name,
                    decision=ActionDecision.SKIP,
                    details="All review comments auto-applied, CI passing — no repair needed",
                )

        # Dispatch the repair
        try:
            comment_id = provider.dispatch_repair(
                pr_number=snapshot.pr_number,
                head_sha=snapshot.head_sha,
                repair_type=repair_type,
                failed_checks=failed_checks,
                review_comments=review_comments,
                review_id=review_context_id,
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
