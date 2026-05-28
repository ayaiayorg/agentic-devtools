"""Request review action — requests Copilot review when needed."""

from __future__ import annotations

import logging

from agentic_devtools.cli.ci.models import COPILOT_REVIEWER_LOGIN
from agentic_devtools.cli.ci.pipeline.models import ActionDecision, ActionResult
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)

_EFFECTIVE_REVIEW_STATES = {"APPROVED", "COMMENTED", "CHANGES_REQUESTED"}


class RequestReviewAction:
    """Request Copilot review when no effective review exists on HEAD.

    Preconditions:
    - PR is not draft (uses DerivedState)
    - No effective Copilot review on HEAD
    - Copilot not already requested as reviewer

    Idempotency: Review exists or pending → skip.
    """

    @property
    def name(self) -> str:
        return "request_review"

    def evaluate(self, snapshot: PRStateSnapshot, derived: DerivedState) -> ActionResult:
        """Evaluate whether Copilot review should be requested."""
        preconditions: dict[str, bool] = {}

        # Must not be draft
        is_draft = derived.is_draft
        preconditions["not_draft"] = not is_draft
        if is_draft:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="PR is a draft",
            )

        # Guard: never request review when repair was just dispatched
        repair_dispatched = getattr(derived, "repair_dispatched", False)
        preconditions["no_repair_dispatched"] = not repair_dispatched
        if repair_dispatched:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="Repair dispatched — deferring review request",
            )

        # Guard: never request review when active coding session is in progress
        preconditions["no_active_session"] = not snapshot.active_session
        if snapshot.active_session:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="Copilot session active — deferring review request",
            )

        # Guard: block review request when unresolved review comments exist
        unresolved = derived.unresolved_threads
        preconditions["no_unresolved_threads"] = unresolved == 0
        if unresolved > 0:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details=f"{unresolved} unresolved thread(s) — deferring review request",
            )

        # CI must be passing before requesting review
        ci_passing = snapshot.ci_status == "passing"
        preconditions["ci_passing"] = ci_passing
        if not ci_passing:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details=f"CI is {snapshot.ci_status} — deferring review request",
            )

        # Check if Copilot already has an effective review on HEAD
        has_effective_review = snapshot.review_state in _EFFECTIVE_REVIEW_STATES and snapshot.copilot_review_id > 0
        preconditions["no_effective_review_on_head"] = not has_effective_review
        if has_effective_review:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details=f"Copilot review exists on HEAD (state={snapshot.review_state})",
            )

        # Check if Copilot is already requested
        copilot_already_requested = derived.copilot_review_pending
        preconditions["not_already_requested"] = not copilot_already_requested
        if copilot_already_requested:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="Copilot review already requested",
            )

        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            preconditions=preconditions,
            details="No Copilot review on HEAD — requesting",
        )

    def execute(
        self,
        provider: CIPlatformProvider,
        snapshot: PRStateSnapshot,
        derived: DerivedState,
    ) -> ActionResult:
        """Request Copilot as a reviewer."""
        try:
            provider.request_reviewer(snapshot.pr_number, COPILOT_REVIEWER_LOGIN)
        except Exception as exc:
            logger.warning("PR #%d: Failed to request Copilot review: %s", snapshot.pr_number, exc)
            return ActionResult(
                name=self.name,
                decision=ActionDecision.FAILED,
                error=str(exc),
                details="Failed to request Copilot review",
            )

        logger.info("PR #%d: Copilot review requested", snapshot.pr_number)
        derived.set("copilot_review_pending", True)
        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            details="Copilot review requested",
        )
