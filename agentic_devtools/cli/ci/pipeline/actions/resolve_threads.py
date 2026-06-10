"""Resolve threads action — resolves review threads from prior commits."""

from __future__ import annotations

import logging

from agentic_devtools.cli.ci.pipeline.models import ActionDecision, ActionResult
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)


class ResolveThreadsAction:
    """Resolve unresolved Copilot review threads from prior commits.

    Preconditions:
    - Unresolved threads exist from prior commits

    Thread resolution is independent of CI status and pending review state.
    Whether a code change addresses a review comment is logically independent
    of whether CI passes or whether a new review has been requested.

    Idempotency: Already-resolved threads are skipped (per-thread).
    """

    @property
    def name(self) -> str:
        return "resolve_threads"

    @property
    def runs_after_invalidation(self) -> bool:
        return True

    def evaluate(self, snapshot: PRStateSnapshot, derived: DerivedState) -> ActionResult:
        """Evaluate whether thread resolution should be attempted."""
        preconditions: dict[str, bool] = {}

        # Unresolved threads exist
        has_threads = snapshot.unresolved_threads > 0
        preconditions["has_unresolved_threads"] = has_threads
        if not has_threads:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="No unresolved threads from prior commits",
            )

        # Skip SDK evaluation when autofix just ran in THIS iteration but no
        # repair has been dispatched. The remaining threads haven't been
        # addressed by any code change — evaluating them wastes tokens.
        autofix_just_ran = derived.get("autofix_applied_this_iteration", False)
        repair_dispatched = derived.get("repair_dispatched", False)
        if autofix_just_ran and not repair_dispatched:
            preconditions["autofix_without_repair"] = True
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details=(
                    "Skipping thread evaluation — autofix just applied but no "
                    "repair dispatched yet; remaining threads have not been addressed"
                ),
            )

        # Skip evaluation when CI is pending/unknown AND no repair has been
        # dispatched. If CI hasn't completed, the repair agent hasn't run
        # yet, so non-autofixed threads can't have been addressed.
        # This prevents token waste on subsequent iterations where CI is
        # still running after an autofix commit.
        ci_status = snapshot.ci_status
        ci_actionable = ci_status in ("passing", "failing")
        if not ci_actionable and not repair_dispatched:
            preconditions["ci_not_actionable"] = True
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details=(
                    f"Skipping thread evaluation — CI is '{ci_status}' and no "
                    "repair dispatched; threads cannot have been addressed yet"
                ),
            )

        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            preconditions=preconditions,
            details=f"{snapshot.unresolved_threads} unresolved thread(s) from prior commit",
        )

    def execute(
        self,
        provider: CIPlatformProvider,
        snapshot: PRStateSnapshot,
        derived: DerivedState,
    ) -> ActionResult:
        """Execute thread resolution via finalize_post_repair.

        Delegates to the provider's finalize_post_repair which handles
        SDK verification and per-thread resolve/keep-open decisions.
        """
        # Find the most recent actionable Copilot review on a prior commit
        from agentic_devtools.cli.ci.models import COPILOT_LOGINS

        prior_reviews = [
            r
            for r in snapshot.reviews
            if r.user in COPILOT_LOGINS
            and r.commit_sha
            and r.commit_sha != snapshot.head_sha
            and r.state in ("CHANGES_REQUESTED", "COMMENTED")
        ]

        if not prior_reviews:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                details="No prior Copilot reviews found (race condition)",
            )

        prior_reviews.sort(key=lambda r: r.id, reverse=True)
        resolved = 0
        unresolved = 0
        skipped_reviews = 0

        for prior_review in prior_reviews:
            try:
                result = provider.finalize_post_repair(
                    pr_number=snapshot.pr_number,
                    base_branch=snapshot.base_branch,
                    head_branch=snapshot.head_branch,
                    head_sha=snapshot.head_sha,
                    review_id=prior_review.id,
                )
            except Exception as exc:
                logger.error("PR #%d: Thread resolution failed: %s", snapshot.pr_number, exc)
                return ActionResult(
                    name=self.name,
                    decision=ActionDecision.FAILED,
                    error=str(exc),
                    details="finalize_post_repair raised an exception",
                )

            if result.skipped:
                skipped_reviews += 1
                continue

            resolved += result.resolved_count
            unresolved += result.unresolved_count

        logger.info(
            "PR #%d: Resolved %d thread(s), %d left open (%d prior review(s), %d skipped)",
            snapshot.pr_number,
            resolved,
            unresolved,
            len(prior_reviews),
            skipped_reviews,
        )
        # Update derived state so downstream actions (approve, merge) see the
        # post-resolution count within the same pipeline run without a
        # re-query.
        #
        # finalize_post_repair() only evaluates unresolved threads associated
        # with the reviewed commit(s) being processed. Preserve unresolved
        # threads that were outside those prior reviews by never dropping below
        # (snapshot.unresolved_threads - resolved).
        unresolved_total = max(unresolved, snapshot.unresolved_threads - resolved, 0)
        derived.set("unresolved_threads", unresolved_total)

        details = f"Resolved {resolved} thread(s), {unresolved_total} left open"
        if skipped_reviews:
            details = f"{details}; skipped {skipped_reviews} prior review(s)"

        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            details=details,
        )
