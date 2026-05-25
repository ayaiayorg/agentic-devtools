"""Tests for RequestReviewAction."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.pipeline.actions.request_review import RequestReviewAction
from agentic_devtools.cli.ci.pipeline.models import ActionDecision
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot


class TestRequestReviewAction:
    """Tests for request review action evaluation and execution."""

    def test_skip_when_draft(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, is_draft=True)
        derived = DerivedState(snapshot)
        action = RequestReviewAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP

    def test_skip_when_ci_not_passing(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, is_draft=False, ci_status="pending")
        derived = DerivedState(snapshot)
        action = RequestReviewAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "ci is pending" in result.details.lower()

    def test_skip_when_review_exists(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            is_draft=False,
            ci_status="passing",
            review_state="APPROVED",
            copilot_review_id=100,
        )
        derived = DerivedState(snapshot)
        action = RequestReviewAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "review exists" in result.details.lower()

    def test_skip_when_already_requested(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            is_draft=False,
            ci_status="passing",
            review_state="",
            copilot_review_id=0,
            copilot_review_pending=True,
        )
        derived = DerivedState(snapshot)
        action = RequestReviewAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "already requested" in result.details.lower()

    def test_skip_when_derived_pending_review_is_true(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            is_draft=False,
            ci_status="passing",
            review_state="",
            copilot_review_id=0,
            copilot_review_pending=False,
        )
        derived = DerivedState(snapshot)
        derived.set("copilot_review_pending", True)
        action = RequestReviewAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "already requested" in result.details.lower()

    def test_execute_when_no_review(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            is_draft=False,
            ci_status="passing",
            review_state="",
            copilot_review_id=0,
            copilot_review_pending=False,
        )
        derived = DerivedState(snapshot)
        action = RequestReviewAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    def test_execute_calls_provider(self) -> None:
        snapshot = PRStateSnapshot(pr_number=42)
        derived = DerivedState(snapshot)
        provider = MagicMock()
        action = RequestReviewAction()
        result = action.execute(provider, snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE
        provider.request_reviewer.assert_called_once()

    def test_execute_sets_derived_pending(self) -> None:
        """execute() must set derived.copilot_review_pending so downstream actions gate correctly."""
        snapshot = PRStateSnapshot(pr_number=42, copilot_review_pending=False)
        derived = DerivedState(snapshot)
        provider = MagicMock()
        action = RequestReviewAction()
        action.execute(provider, snapshot, derived)
        assert derived.copilot_review_pending is True
        # Snapshot itself must remain unchanged (frozen)
        assert snapshot.copilot_review_pending is False
