"""Tests for the RebaseAction pipeline action."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.pipeline.actions.rebase import RebaseAction
from agentic_devtools.cli.ci.pipeline.exceptions import ForceWithLeaseError, RebaseConflictError
from agentic_devtools.cli.ci.pipeline.models import ActionDecision
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot


class TestRebaseAction:
    """Tests for rebase action evaluation and execution."""

    def _make_snapshot(self, **kwargs: object) -> PRStateSnapshot:
        """Create a PRStateSnapshot with sensible defaults."""
        defaults: dict[str, object] = {
            "pr_number": 42,
            "head_sha": "abc123",
            "base_branch": "main",
            "head_branch": "feature/foo",
            "commit_count": 1,
            "commits_behind": 0,
            "base_repo_full_name": "owner/repo",
        }
        defaults.update(kwargs)
        return PRStateSnapshot(**defaults)  # type: ignore[arg-type]

    def test_name_property(self) -> None:
        """RebaseAction.name returns 'rebase'."""
        action = RebaseAction()
        assert action.name == "rebase"

    def test_does_not_set_runs_after_invalidation(self) -> None:
        """RebaseAction does NOT set runs_after_invalidation."""
        action = RebaseAction()
        assert not getattr(action, "runs_after_invalidation", False)

    @patch(
        "agentic_devtools.cli.ci.pipeline.actions.rebase.is_copilot_session_active_via_agent_task",
        return_value=False,
    )
    def test_evaluate_skip_when_up_to_date(self, _mock_session) -> None:
        """evaluate() returns SKIP when commits_behind == 0."""
        snapshot = self._make_snapshot(commits_behind=0)
        derived = DerivedState(snapshot)
        action = RebaseAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert result.preconditions["commits_behind_gt_0"] is False

    @patch(
        "agentic_devtools.cli.ci.pipeline.actions.rebase.is_copilot_session_active_via_agent_task",
        return_value=False,
    )
    def test_evaluate_execute_when_behind(self, _mock_session) -> None:
        """evaluate() returns EXECUTE when commits_behind > 0."""
        snapshot = self._make_snapshot(commits_behind=3)
        derived = DerivedState(snapshot)
        action = RebaseAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE
        assert result.preconditions["commits_behind_gt_0"] is True
        assert "3" in result.details

    @patch(
        "agentic_devtools.cli.ci.pipeline.actions.rebase.is_copilot_session_active_via_agent_task",
        return_value=False,
    )
    def test_evaluate_skip_when_repair_dispatched(self, _mock_session) -> None:
        """evaluate() returns SKIP when repair_dispatched is True."""
        snapshot = self._make_snapshot(commits_behind=2)
        derived = DerivedState(snapshot)
        derived.set("repair_dispatched", True)
        action = RebaseAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert result.preconditions["no_repair_dispatched"] is False

    @patch(
        "agentic_devtools.cli.ci.pipeline.actions.rebase.is_copilot_session_active_via_agent_task",
        return_value=True,
    )
    def test_evaluate_skip_when_active_session(self, _mock_session) -> None:
        """evaluate() returns SKIP when active copilot session detected."""
        snapshot = self._make_snapshot(commits_behind=2)
        derived = DerivedState(snapshot)
        action = RebaseAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert result.preconditions["no_active_session"] is False

    @patch(
        "agentic_devtools.cli.ci.pipeline.actions.rebase.is_copilot_session_active_via_agent_task",
        return_value=False,
    )
    def test_evaluate_preconditions_structure(self, _mock_session) -> None:
        """evaluate() includes no_repair_dispatched and no_active_session keys."""
        snapshot = self._make_snapshot(commits_behind=1)
        derived = DerivedState(snapshot)
        action = RebaseAction()
        result = action.evaluate(snapshot, derived)
        assert "no_repair_dispatched" in result.preconditions
        assert "no_active_session" in result.preconditions

    @patch(
        "agentic_devtools.cli.ci.pipeline.actions.rebase.is_copilot_session_active_via_agent_task",
        return_value=False,
    )
    def test_evaluate_skip_when_workflow_files_changed(self, _mock_session) -> None:
        """evaluate() returns SKIP when workflow files are modified."""
        snapshot = self._make_snapshot(
            commits_behind=1,
            files=[".github/workflows/ai-pr-loop.yml"],
        )
        derived = DerivedState(snapshot)
        action = RebaseAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert result.preconditions["no_workflow_file_changes"] is False
        assert "workflow files changed" in result.details.lower()

    @patch(
        "agentic_devtools.cli.ci.pipeline.actions.rebase.is_copilot_session_active_via_agent_task",
        return_value=False,
    )
    def test_evaluate_includes_commits_behind_in_details(self, _mock_session) -> None:
        """evaluate() includes commits_behind count in details."""
        snapshot = self._make_snapshot(commits_behind=5)
        derived = DerivedState(snapshot)
        action = RebaseAction()
        result = action.evaluate(snapshot, derived)
        assert "5" in result.details

    @patch(
        "agentic_devtools.cli.ci.pipeline.actions.rebase.is_copilot_session_active_via_agent_task",
        return_value=False,
    )
    def test_evaluate_no_io(self, mock_session) -> None:
        """evaluate() completes without calling provider methods (pure data access)."""
        snapshot = self._make_snapshot(commits_behind=0)
        derived = DerivedState(snapshot)
        action = RebaseAction()
        # evaluate should not call any provider method (no provider arg)
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP

    def test_execute_calls_rebase_onto_base(self) -> None:
        """execute() calls provider.rebase_onto_base() with correct args."""
        snapshot = self._make_snapshot(commits_behind=2, base_branch="develop")
        derived = DerivedState(snapshot)
        provider = MagicMock()
        action = RebaseAction()
        result = action.execute(provider, snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE
        provider.rebase_onto_base.assert_called_once_with(
            pr_number=42,
            base_branch="develop",
            head_branch="feature/foo",
            head_sha="abc123",
        )

    def test_execute_returns_invalidates_snapshot_on_success(self) -> None:
        """execute() returns invalidates_snapshot=True on success."""
        snapshot = self._make_snapshot(commits_behind=1)
        derived = DerivedState(snapshot)
        provider = MagicMock()
        action = RebaseAction()
        result = action.execute(provider, snapshot, derived)
        assert result.invalidates_snapshot is True

    def test_execute_returns_blocked_on_conflict(self) -> None:
        """execute() returns BLOCKED on RebaseConflictError."""
        snapshot = self._make_snapshot(commits_behind=1)
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.rebase_onto_base.side_effect = RebaseConflictError("conflicts")
        action = RebaseAction()
        result = action.execute(provider, snapshot, derived)
        assert result.decision == ActionDecision.BLOCKED
        assert "conflict" in result.details.lower()

    def test_execute_returns_failed_on_force_with_lease_error(self) -> None:
        """execute() returns FAILED on ForceWithLeaseError."""
        snapshot = self._make_snapshot(commits_behind=1)
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.rebase_onto_base.side_effect = ForceWithLeaseError("lease failed")
        action = RebaseAction()
        result = action.execute(provider, snapshot, derived)
        assert result.decision == ActionDecision.FAILED
        assert "lease" in result.details.lower() or "force" in result.details.lower()

    def test_execute_handles_generic_exception(self) -> None:
        """execute() returns FAILED on generic exception."""
        snapshot = self._make_snapshot(commits_behind=1)
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.rebase_onto_base.side_effect = RuntimeError("unexpected")
        action = RebaseAction()
        result = action.execute(provider, snapshot, derived)
        assert result.decision == ActionDecision.FAILED
        assert "unexpected" in result.error

    def test_execute_details_include_base_branch(self) -> None:
        """execute() success details mention base branch."""
        snapshot = self._make_snapshot(commits_behind=2, base_branch="main")
        derived = DerivedState(snapshot)
        provider = MagicMock()
        action = RebaseAction()
        result = action.execute(provider, snapshot, derived)
        assert "main" in result.details
