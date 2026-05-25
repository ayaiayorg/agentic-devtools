"""Tests for SquashAction."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.pipeline.actions.squash import SquashAction
from agentic_devtools.cli.ci.pipeline.models import ActionDecision
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot


class TestSquashAction:
    """Tests for squash action evaluation."""

    def test_skip_when_single_commit(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, commit_count=1, ci_status="passing")
        derived = DerivedState(snapshot)
        action = SquashAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "1 commit" in result.details

    def test_skip_when_active_session(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, commit_count=3, active_session=True, ci_status="passing")
        derived = DerivedState(snapshot)
        action = SquashAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "active" in result.details.lower()

    def test_skip_when_ci_not_passing(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, commit_count=3, ci_status="failing")
        derived = DerivedState(snapshot)
        action = SquashAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "failing" in result.details.lower()

    def test_execute_when_multiple_commits_and_ci_passing(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            commit_count=3,
            ci_status="passing",
            active_session=False,
            copilot_review_pending=False,
        )
        derived = DerivedState(snapshot)
        action = SquashAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    def test_skip_when_derived_pending_review_is_true(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            commit_count=3,
            ci_status="passing",
            copilot_review_pending=False,
        )
        derived = DerivedState(snapshot)
        derived.set("copilot_review_pending", True)
        action = SquashAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "pending" in result.details.lower()

    def test_execute_calls_squash(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            commit_count=3,
            head_sha="abc",
            base_branch="main",
            head_branch="feature",
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        action = SquashAction()
        result = action.execute(provider, snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE
        assert result.invalidates_snapshot is True
        provider.squash_post_repair.assert_called_once()
        assert derived.commit_count == 1

    def test_execute_returns_failed_when_squash_raises(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            commit_count=3,
            head_sha="abc",
            base_branch="main",
            head_branch="feature",
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.squash_post_repair.side_effect = RuntimeError("squash failed")
        action = SquashAction()
        result = action.execute(provider, snapshot, derived)
        assert result.decision == ActionDecision.FAILED
        assert result.details == "squash_post_repair failed"
        assert result.error == "squash failed"
