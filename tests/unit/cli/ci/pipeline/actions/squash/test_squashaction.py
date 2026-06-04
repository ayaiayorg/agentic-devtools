"""Tests for SquashAction."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.pipeline.actions.squash import SquashAction
from agentic_devtools.cli.ci.pipeline.models import ActionDecision
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot


class TestSquashAction:
    """Tests for squash action evaluation."""

    def test_skip_when_single_commit(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, commit_count=1, ci_status="passing")
        derived = DerivedState(snapshot)
        action = SquashAction()
        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.squash.is_copilot_session_active_via_agent_task",
            return_value=False,
        ):
            result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "1 commit" in result.details

    def test_skip_when_active_session(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, commit_count=3, ci_status="passing", base_repo_full_name="owner/repo")
        derived = DerivedState(snapshot)
        action = SquashAction()
        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.squash.is_copilot_session_active_via_agent_task",
            return_value=True,
        ) as mock_detector:
            result = action.evaluate(snapshot, derived)
            mock_detector.assert_called_once_with("owner/repo", 1)
        assert result.decision == ActionDecision.SKIP
        assert "active" in result.details.lower()

    def test_skip_when_repair_dispatched(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, commit_count=3, ci_status="passing")
        derived = DerivedState(snapshot)
        derived.set("repair_dispatched", True)
        action = SquashAction()
        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.squash.is_copilot_session_active_via_agent_task",
            return_value=False,
        ):
            result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "repair dispatched" in result.details.lower()

    def test_skip_when_unresolved_threads_remain(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, commit_count=3, ci_status="passing", unresolved_threads=2)
        derived = DerivedState(snapshot)
        action = SquashAction()
        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.squash.is_copilot_session_active_via_agent_task",
            return_value=False,
        ):
            result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert result.preconditions["all_threads_resolved"] is False
        assert "unresolved_threads" in result.details

    def test_execute_when_unresolved_threads_zero(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, commit_count=3, ci_status="passing", unresolved_threads=0)
        derived = DerivedState(snapshot)
        action = SquashAction()
        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.squash.is_copilot_session_active_via_agent_task",
            return_value=False,
        ):
            result = action.evaluate(snapshot, derived)
        assert result.preconditions["all_threads_resolved"] is True
        assert result.decision == ActionDecision.EXECUTE

    def test_execute_when_derived_unresolved_threads_override_is_zero(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, commit_count=3, ci_status="passing", unresolved_threads=3)
        derived = DerivedState(snapshot)
        derived.set("unresolved_threads", 0)
        action = SquashAction()
        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.squash.is_copilot_session_active_via_agent_task",
            return_value=False,
        ):
            result = action.evaluate(snapshot, derived)
        assert result.preconditions["all_threads_resolved"] is True
        assert result.decision == ActionDecision.EXECUTE

    def test_execute_when_multiple_commits(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            commit_count=3,
            ci_status="passing",
            copilot_review_pending=False,
        )
        derived = DerivedState(snapshot)
        action = SquashAction()
        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.squash.is_copilot_session_active_via_agent_task",
            return_value=False,
        ):
            result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    def test_skip_when_ci_pending(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, commit_count=3, ci_status="pending")
        derived = DerivedState(snapshot)
        action = SquashAction()
        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.squash.is_copilot_session_active_via_agent_task",
            return_value=False,
        ):
            result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "ci is pending" in result.details.lower()

    def test_skip_when_ci_failing(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, commit_count=3, ci_status="failing")
        derived = DerivedState(snapshot)
        action = SquashAction()
        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.squash.is_copilot_session_active_via_agent_task",
            return_value=False,
        ):
            result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "ci is failing" in result.details.lower()

    def test_execute_when_derived_pending_review_is_true(self) -> None:
        """Pending review does NOT block squash — only active session does."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            commit_count=3,
            ci_status="passing",
            copilot_review_pending=False,
        )
        derived = DerivedState(snapshot)
        derived.set("copilot_review_pending", True)
        action = SquashAction()
        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.squash.is_copilot_session_active_via_agent_task",
            return_value=False,
        ):
            result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

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
