"""Tests for ApproveAction."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.models import ReviewInfo
from agentic_devtools.cli.ci.pipeline.actions.approve import ApproveAction
from agentic_devtools.cli.ci.pipeline.models import ActionDecision
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot


class TestApproveAction:
    """Tests for approve action evaluation."""

    def test_skip_when_already_approved(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, has_approval_on_head=True, ci_status="passing")
        derived = DerivedState(snapshot)
        action = ApproveAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "already approved" in result.details.lower()

    def test_skip_when_ci_not_passing(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, has_approval_on_head=False, ci_status="failing")
        derived = DerivedState(snapshot)
        action = ApproveAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "failing" in result.details.lower()

    def test_skip_when_review_not_clean(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            has_approval_on_head=False,
            ci_status="passing",
            review_state="CHANGES_REQUESTED",
            copilot_review_id=1,
            copilot_review_inline_count=2,
        )
        derived = DerivedState(snapshot)
        action = ApproveAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "not clean" in result.details.lower()

    def test_skip_when_unresolved_threads(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            has_approval_on_head=False,
            ci_status="passing",
            review_state="APPROVED",
            copilot_review_id=1,
            unresolved_threads=2,
        )
        derived = DerivedState(snapshot)
        action = ApproveAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "unresolved" in result.details.lower()

    def test_skip_when_derived_unresolved_threads_nonzero(self) -> None:
        """Approval is blocked when DerivedState overrides unresolved_threads to > 0."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            has_approval_on_head=False,
            ci_status="passing",
            review_state="APPROVED",
            copilot_review_id=1,
            unresolved_threads=0,
        )
        derived = DerivedState(snapshot)
        derived.set("unresolved_threads", 1)
        action = ApproveAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "unresolved" in result.details.lower()

    def test_proceed_when_derived_clears_unresolved_threads(self) -> None:
        """Approval can proceed when DerivedState sets unresolved_threads to 0."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            has_approval_on_head=False,
            ci_status="passing",
            review_state="APPROVED",
            copilot_review_id=1,
            unresolved_threads=2,  # stale snapshot value
        )
        derived = DerivedState(snapshot)
        derived.set("unresolved_threads", 0)  # ResolveThreadsAction updated this
        action = ApproveAction()
        result = action.evaluate(snapshot, derived)
        # Passes no_unresolved_threads; should proceed to EXECUTE
        assert result.preconditions.get("no_unresolved_threads") is True

    def test_skip_when_non_copilot_changes_requested_on_head(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            head_sha="head-sha",
            has_approval_on_head=False,
            ci_status="passing",
            review_state="APPROVED",
            copilot_review_id=1,
            unresolved_threads=0,
            reviews=[
                ReviewInfo(id=10, user="alice", state="CHANGES_REQUESTED", commit_sha="head-sha"),
            ],
        )
        derived = DerivedState(snapshot)
        action = ApproveAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "requested changes" in result.details.lower()

    def test_execute_when_all_conditions_met(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            has_approval_on_head=False,
            ci_status="passing",
            review_state="APPROVED",
            copilot_review_id=1,
            unresolved_threads=0,
        )
        derived = DerivedState(snapshot)
        action = ApproveAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    def test_execute_calls_provider(self) -> None:
        snapshot = PRStateSnapshot(pr_number=42, head_sha="sha123")
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.approve_pr.return_value = True
        action = ApproveAction()
        result = action.execute(provider, snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE
        provider.approve_pr.assert_called_once_with(42, "sha123", "Auto-approved by AI PR loop")
        assert derived.has_approval_on_head is True

    def test_execute_skips_when_provider_skips_approval(self) -> None:
        snapshot = PRStateSnapshot(pr_number=42, head_sha="sha123")
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.approve_pr.return_value = False
        action = ApproveAction()

        result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.SKIP
        assert result.preconditions == {"approver_token_available": False}
        assert "skipped approval" in result.details.lower()
        assert derived.has_approval_on_head is False
