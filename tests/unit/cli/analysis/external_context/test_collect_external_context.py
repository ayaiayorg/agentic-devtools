"""Tests for collect_external_context()."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agentic_devtools.cli.analysis.external_context import (
    ExternalContext,
    collect_external_context,
)


class TestCollectExternalContext:
    """Tests for external worktree context collection."""

    def test_static_only_returns_none(self, tmp_path):
        """--static-only flag → None (no scanning)."""
        result = collect_external_context(tmp_path, "PROJ-1", static_only=True)
        assert result is None

    def test_no_external_worktrees_returns_none(self, tmp_path):
        """No external worktrees found → None."""
        with patch(
            "agentic_devtools.cli.analysis.external_context._discover_worktrees",
            return_value=[],
        ):
            result = collect_external_context(tmp_path, "PROJ-1")
            assert result is None

    def test_external_worktrees_with_logs(self, tmp_path):
        """External worktrees with matching logs → populated ExternalContext."""
        wt_path = tmp_path / "ext-worktree"
        wt_logs = wt_path / ".agdt" / "workflows" / "alice" / "PROJ-1" / "background-tasks" / "logs"
        wt_logs.mkdir(parents=True)
        (wt_logs / "task.log").write_text("log content here\n" * 10, encoding="utf-8")

        with patch(
            "agentic_devtools.cli.analysis.external_context._discover_worktrees",
            return_value=[str(wt_path)],
        ):
            result = collect_external_context(tmp_path, "PROJ-1")

        assert result is not None
        assert isinstance(result, ExternalContext)
        assert len(result.log_evidence) == 1
        assert result.log_evidence[0].identity == "alice"
        assert "log content here" in result.log_evidence[0].excerpt
        assert str(wt_path) in result.worktrees_scanned

    def test_external_worktree_no_matching_logs(self, tmp_path):
        """External worktree without matching worktree_key logs → ExternalContext with empty evidence."""
        wt_path = tmp_path / "ext-worktree"
        wt_logs = wt_path / ".agdt" / "workflows" / "alice" / "OTHER-KEY" / "background-tasks" / "logs"
        wt_logs.mkdir(parents=True)
        (wt_logs / "task.log").write_text("log content", encoding="utf-8")

        with patch(
            "agentic_devtools.cli.analysis.external_context._discover_worktrees",
            return_value=[str(wt_path)],
        ):
            result = collect_external_context(tmp_path, "PROJ-1")

        assert result is not None
        assert result.log_evidence == []
        assert str(wt_path) in result.worktrees_scanned
        assert "alice" in result.identities_scanned

    def test_log_truncation(self, tmp_path):
        """Logs exceeding 500 lines are truncated with header."""
        wt_path = tmp_path / "ext-worktree"
        wt_logs = wt_path / ".agdt" / "workflows" / "alice" / "PROJ-1" / "background-tasks" / "logs"
        wt_logs.mkdir(parents=True)
        # Write 600 lines
        (wt_logs / "task.log").write_text("\n".join(f"line {i}" for i in range(600)), encoding="utf-8")

        with patch(
            "agentic_devtools.cli.analysis.external_context._discover_worktrees",
            return_value=[str(wt_path)],
        ):
            result = collect_external_context(tmp_path, "PROJ-1")

        assert result is not None
        assert "[…truncated 100 lines…]" in result.log_evidence[0].excerpt

    def test_identities_scanned_includes_visited_without_evidence(self, tmp_path):
        """identities_scanned includes identities visited even without logs."""
        wt_path = tmp_path / "ext-worktree"
        wt_wf = wt_path / ".agdt" / "workflows"
        # alice has matching logs
        wt_logs = wt_wf / "alice" / "PROJ-1" / "background-tasks" / "logs"
        wt_logs.mkdir(parents=True)
        (wt_logs / "task.log").write_text("log content", encoding="utf-8")
        # bob is a valid identity dir but has no matching worktree_key logs
        (wt_wf / "bob" / "OTHER-KEY").mkdir(parents=True)

        with patch(
            "agentic_devtools.cli.analysis.external_context._discover_worktrees",
            return_value=[str(wt_path)],
        ):
            result = collect_external_context(tmp_path, "PROJ-1")

        assert result is not None
        # bob should be in identities_scanned even though no evidence was found
        assert "alice" in result.identities_scanned
        assert "bob" in result.identities_scanned

    def test_unsafe_identity_dir_name_skipped(self, tmp_path):
        """Identity dir with unsafe name (path traversal) is skipped."""
        wt_path = tmp_path / "ext-worktree"
        wt_wf = wt_path / ".agdt" / "workflows"
        # Create a valid identity with logs
        valid_logs = wt_wf / "alice" / "PROJ-1" / "background-tasks" / "logs"
        valid_logs.mkdir(parents=True)
        (valid_logs / "task.log").write_text("log content", encoding="utf-8")
        # Create an identity dir with an unsafe name (contains `..` / path traversal)
        unsafe_dir = wt_wf / "bad..name"
        unsafe_dir.mkdir(parents=True)

        with patch(
            "agentic_devtools.cli.analysis.external_context._discover_worktrees",
            return_value=[str(wt_path)],
        ):
            result = collect_external_context(tmp_path, "PROJ-1")

        assert result is not None
        # alice logs should be found
        assert len(result.log_evidence) == 1
        assert result.log_evidence[0].identity == "alice"
        # unsafe identity dir should NOT be in identities_scanned
        assert "bad..name" not in result.identities_scanned
        assert "alice" in result.identities_scanned

    def test_unsafe_worktree_key_raises_value_error(self, tmp_path):
        """Unsafe worktree_key with path traversal → ValueError."""
        wt_path = tmp_path / "ext-worktree"
        wt_wf = wt_path / ".agdt" / "workflows" / "alice"
        wt_wf.mkdir(parents=True)

        with (
            patch(
                "agentic_devtools.cli.analysis.external_context._discover_worktrees",
                return_value=[str(wt_path)],
            ),
            pytest.raises(ValueError, match="not a safe directory segment"),
        ):
            collect_external_context(tmp_path, "../escape")

    def test_worktrees_scanned_includes_all_scanned(self, tmp_path):
        """worktrees_scanned includes all worktrees with workflows dirs, not just those with evidence."""
        wt1 = tmp_path / "wt1"
        wt2 = tmp_path / "wt2"
        # wt1 has matching logs
        wt1_logs = wt1 / ".agdt" / "workflows" / "alice" / "PROJ-1" / "background-tasks" / "logs"
        wt1_logs.mkdir(parents=True)
        (wt1_logs / "task.log").write_text("log content", encoding="utf-8")
        # wt2 has workflows dir but no matching logs
        (wt2 / ".agdt" / "workflows" / "bob").mkdir(parents=True)

        with patch(
            "agentic_devtools.cli.analysis.external_context._discover_worktrees",
            return_value=[str(wt1), str(wt2)],
        ):
            result = collect_external_context(tmp_path, "PROJ-1")

        assert result is not None
        assert str(wt1) in result.worktrees_scanned
        assert str(wt2) in result.worktrees_scanned
        assert len(result.log_evidence) == 1

    def test_permission_error_on_identity_iterdir_continues(self, tmp_path):
        """PermissionError iterating identity dirs → worktree still scanned, no crash."""
        wt_path = tmp_path / "ext-worktree"
        wt_wf = wt_path / ".agdt" / "workflows"
        wt_wf.mkdir(parents=True)
        (wt_wf / "alice").mkdir()

        original_iterdir = type(wt_wf).iterdir

        def _selective_iterdir(self_path):
            if self_path.name == "workflows" and "ext-worktree" in str(self_path):
                raise PermissionError("denied")
            return original_iterdir(self_path)

        with (
            patch(
                "agentic_devtools.cli.analysis.external_context._discover_worktrees",
                return_value=[str(wt_path)],
            ),
            patch.object(type(wt_wf), "iterdir", autospec=True, side_effect=_selective_iterdir),
        ):
            result = collect_external_context(tmp_path, "PROJ-1")

        assert result is not None
        assert str(wt_path) in result.worktrees_scanned
        assert result.log_evidence == []

    def test_non_dir_identity_entry_skipped(self, tmp_path):
        """Regular files inside workflows/ are skipped."""
        wt_path = tmp_path / "ext-worktree"
        wt_wf = wt_path / ".agdt" / "workflows"
        wt_wf.mkdir(parents=True)
        (wt_wf / "some_file.txt").write_text("not a dir", encoding="utf-8")
        # Also add a valid identity to make the worktree scannable
        (wt_wf / "alice" / "PROJ-1").mkdir(parents=True)

        with patch(
            "agentic_devtools.cli.analysis.external_context._discover_worktrees",
            return_value=[str(wt_path)],
        ):
            result = collect_external_context(tmp_path, "PROJ-1")

        assert result is not None
        assert "alice" in result.identities_scanned

    def test_unscoped_identity_dir_skipped(self, tmp_path):
        """_unscoped identity directory is excluded."""
        wt_path = tmp_path / "ext-worktree"
        wt_wf = wt_path / ".agdt" / "workflows"
        (wt_wf / "_unscoped" / "PROJ-1" / "background-tasks" / "logs").mkdir(parents=True)
        (wt_wf / "alice" / "PROJ-1").mkdir(parents=True)

        with patch(
            "agentic_devtools.cli.analysis.external_context._discover_worktrees",
            return_value=[str(wt_path)],
        ):
            result = collect_external_context(tmp_path, "PROJ-1")

        assert result is not None
        assert "_unscoped" not in result.identities_scanned
        assert "alice" in result.identities_scanned

    def test_safe_identity_dir_included(self, tmp_path):
        """Identity dirs with safe names are included in scanning."""
        wt_path = tmp_path / "ext-worktree"
        wt_wf = wt_path / ".agdt" / "workflows"
        wt_wf.mkdir(parents=True)
        # Create a safe identity to make worktree scannable
        (wt_wf / "alice" / "PROJ-1").mkdir(parents=True)

        with patch(
            "agentic_devtools.cli.analysis.external_context._discover_worktrees",
            return_value=[str(wt_path)],
        ):
            result = collect_external_context(tmp_path, "PROJ-1")

        assert result is not None
        assert "alice" in result.identities_scanned

    def test_permission_error_on_log_iterdir_continues(self, tmp_path):
        """PermissionError iterating log files → identity still scanned."""
        wt_path = tmp_path / "ext-worktree"
        wt_wf = wt_path / ".agdt" / "workflows"
        logs_dir = wt_wf / "alice" / "PROJ-1" / "background-tasks" / "logs"
        logs_dir.mkdir(parents=True)

        original_iterdir = type(logs_dir).iterdir

        def _selective_iterdir(self_path):
            if self_path.name == "logs":
                raise PermissionError("denied")
            return original_iterdir(self_path)

        with (
            patch(
                "agentic_devtools.cli.analysis.external_context._discover_worktrees",
                return_value=[str(wt_path)],
            ),
            patch.object(type(logs_dir), "iterdir", autospec=True, side_effect=_selective_iterdir),
        ):
            result = collect_external_context(tmp_path, "PROJ-1")

        assert result is not None
        assert "alice" in result.identities_scanned
        assert result.log_evidence == []

    def test_non_file_log_entry_skipped(self, tmp_path):
        """Directories inside logs/ are skipped (only files collected)."""
        wt_path = tmp_path / "ext-worktree"
        wt_wf = wt_path / ".agdt" / "workflows"
        logs_dir = wt_wf / "alice" / "PROJ-1" / "background-tasks" / "logs"
        logs_dir.mkdir(parents=True)
        (logs_dir / "subdir").mkdir()
        (logs_dir / "actual.log").write_text("real log", encoding="utf-8")

        with patch(
            "agentic_devtools.cli.analysis.external_context._discover_worktrees",
            return_value=[str(wt_path)],
        ):
            result = collect_external_context(tmp_path, "PROJ-1")

        assert result is not None
        assert len(result.log_evidence) == 1
        assert "actual.log" in result.log_evidence[0].log_file

    def test_os_error_on_getmtime_skips_log(self, tmp_path):
        """OSError on os.path.getmtime → that log file is skipped."""
        wt_path = tmp_path / "ext-worktree"
        wt_wf = wt_path / ".agdt" / "workflows"
        logs_dir = wt_wf / "alice" / "PROJ-1" / "background-tasks" / "logs"
        logs_dir.mkdir(parents=True)
        (logs_dir / "task.log").write_text("log content", encoding="utf-8")

        with (
            patch(
                "agentic_devtools.cli.analysis.external_context._discover_worktrees",
                return_value=[str(wt_path)],
            ),
            patch("os.path.getmtime", side_effect=OSError("cannot stat")),
        ):
            result = collect_external_context(tmp_path, "PROJ-1")

        assert result is not None
        assert result.log_evidence == []

    def test_no_worktrees_with_workflows_returns_none(self, tmp_path):
        """External worktrees without .agdt/workflows/ → None."""
        wt_path = tmp_path / "ext-worktree"
        wt_path.mkdir()
        # No .agdt/workflows/ directory

        with patch(
            "agentic_devtools.cli.analysis.external_context._discover_worktrees",
            return_value=[str(wt_path)],
        ):
            result = collect_external_context(tmp_path, "PROJ-1")

        assert result is None
