"""Tests for list_worktree_state_dirs()."""

from __future__ import annotations

import pytest

from agentic_devtools.cli.analysis.context_resolver import (
    WorktreeStateDir,
    list_worktree_state_dirs,
)


class TestListWorktreeStateDirs:
    """Tests for discovering state dirs across identities."""

    def test_multiple_identities_found(self, tmp_path):
        """Multiple identity dirs containing the worktree_key are returned."""
        wf = tmp_path / ".agdt" / "workflows"
        (wf / "alice" / "PROJ-1").mkdir(parents=True)
        (wf / "bob" / "PROJ-1").mkdir(parents=True)

        result = list_worktree_state_dirs(tmp_path, "PROJ-1")

        assert len(result) == 2
        names = [r.identity for r in result]
        assert names == ["alice", "bob"]  # sorted
        assert all(isinstance(r, WorktreeStateDir) for r in result)

    def test_no_matching_directories(self, tmp_path):
        """No identity dirs contain the worktree_key → empty list."""
        wf = tmp_path / ".agdt" / "workflows"
        (wf / "alice" / "OTHER-KEY").mkdir(parents=True)

        result = list_worktree_state_dirs(tmp_path, "PROJ-1")
        assert result == []

    def test_unscoped_directory_skipped(self, tmp_path):
        """The _unscoped directory is always excluded."""
        wf = tmp_path / ".agdt" / "workflows"
        (wf / "_unscoped" / "PROJ-1").mkdir(parents=True)
        (wf / "alice" / "PROJ-1").mkdir(parents=True)

        result = list_worktree_state_dirs(tmp_path, "PROJ-1")
        assert len(result) == 1
        assert result[0].identity == "alice"

    def test_has_logs_detected(self, tmp_path):
        """has_logs is True when background-tasks/logs/ exists."""
        wf = tmp_path / ".agdt" / "workflows"
        state_dir = wf / "alice" / "PROJ-1"
        state_dir.mkdir(parents=True)
        (state_dir / "background-tasks" / "logs").mkdir(parents=True)

        result = list_worktree_state_dirs(tmp_path, "PROJ-1")
        assert result[0].has_logs is True

    def test_has_logs_false_when_no_logs_dir(self, tmp_path):
        """has_logs is False when background-tasks/logs/ does not exist."""
        wf = tmp_path / ".agdt" / "workflows"
        (wf / "alice" / "PROJ-1").mkdir(parents=True)

        result = list_worktree_state_dirs(tmp_path, "PROJ-1")
        assert result[0].has_logs is False

    def test_missing_workflows_dir(self, tmp_path):
        """No .agdt/workflows/ → empty list."""
        result = list_worktree_state_dirs(tmp_path, "PROJ-1")
        assert result == []

    def test_unsafe_worktree_key_raises(self, tmp_path):
        """Worktree key with path traversal is rejected."""
        with pytest.raises(ValueError, match="not a safe directory segment"):
            list_worktree_state_dirs(tmp_path, "../escape")
