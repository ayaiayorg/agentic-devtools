"""Tests for scan_identity_logs()."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agentic_devtools.cli.analysis.identity_scanner import (
    LogEvidence,
    scan_identity_logs,
)


class TestScanIdentityLogs:
    """Tests for multi-identity log scanning."""

    def test_logs_found_across_identities(self, tmp_path):
        """Logs from multiple identity dirs are collected."""
        wf = tmp_path / ".agdt" / "workflows"
        logs_a = wf / "alice" / "PROJ-1" / "background-tasks" / "logs"
        logs_b = wf / "bob" / "PROJ-1" / "background-tasks" / "logs"
        logs_a.mkdir(parents=True)
        logs_b.mkdir(parents=True)
        (logs_a / "task_20260101.log").write_text("log a", encoding="utf-8")
        (logs_b / "task_20260102.log").write_text("log b", encoding="utf-8")

        result = scan_identity_logs(tmp_path, "PROJ-1")
        assert len(result) == 2
        identities = [r.identity for r in result]
        assert "alice" in identities
        assert "bob" in identities
        assert all(isinstance(r, LogEvidence) for r in result)

    def test_workflow_name_filter(self, tmp_path):
        """Only logs matching workflow_name in filename are returned."""
        wf = tmp_path / ".agdt" / "workflows"
        logs = wf / "alice" / "PROJ-1" / "background-tasks" / "logs"
        logs.mkdir(parents=True)
        (logs / "pr_review_20260101.log").write_text("pr review", encoding="utf-8")
        (logs / "git_save_20260101.log").write_text("git save", encoding="utf-8")

        result = scan_identity_logs(tmp_path, "PROJ-1", workflow_name="pr-review")
        assert len(result) == 1
        assert "pr_review" in result[0].path.name

    def test_no_logs_found(self, tmp_path):
        """No matching logs → empty list."""
        wf = tmp_path / ".agdt" / "workflows"
        (wf / "alice" / "PROJ-1").mkdir(parents=True)

        result = scan_identity_logs(tmp_path, "PROJ-1")
        assert result == []

    def test_empty_identity_dirs_skipped(self, tmp_path):
        """Identity dirs without the worktree_key are skipped."""
        wf = tmp_path / ".agdt" / "workflows"
        (wf / "alice" / "OTHER-KEY" / "background-tasks" / "logs").mkdir(parents=True)

        result = scan_identity_logs(tmp_path, "PROJ-1")
        assert result == []

    def test_identity_attribution(self, tmp_path):
        """LogEvidence.identity is the directory name, not the owner email."""
        wf = tmp_path / ".agdt" / "workflows"
        logs = wf / "alice" / "PROJ-1" / "background-tasks" / "logs"
        logs.mkdir(parents=True)
        (logs / "task.log").write_text("data", encoding="utf-8")
        # Write an .identity-owner file to ensure it's NOT used for identity
        (wf / "alice" / ".identity-owner").write_text("alice@example.com", encoding="utf-8")

        result = scan_identity_logs(tmp_path, "PROJ-1")
        assert result[0].identity == "alice"

    def test_unscoped_excluded(self, tmp_path):
        """_unscoped directory is excluded from scanning."""
        wf = tmp_path / ".agdt" / "workflows"
        logs = wf / "_unscoped" / "PROJ-1" / "background-tasks" / "logs"
        logs.mkdir(parents=True)
        (logs / "task.log").write_text("data", encoding="utf-8")

        result = scan_identity_logs(tmp_path, "PROJ-1")
        assert result == []

    def test_missing_workflows_dir(self, tmp_path):
        """No .agdt/workflows/ → empty list."""
        result = scan_identity_logs(tmp_path, "PROJ-1")
        assert result == []

    def test_deterministic_ordering(self, tmp_path):
        """Results are sorted by identity then path."""
        wf = tmp_path / ".agdt" / "workflows"
        for name in ["charlie", "alice", "bob"]:
            logs = wf / name / "PROJ-1" / "background-tasks" / "logs"
            logs.mkdir(parents=True)
            (logs / "task.log").write_text("data", encoding="utf-8")

        result = scan_identity_logs(tmp_path, "PROJ-1")
        assert [r.identity for r in result] == ["alice", "bob", "charlie"]

    def test_permission_error_on_log_iterdir_skipped(self, tmp_path):
        """PermissionError when listing log files in a logs dir is handled gracefully."""
        wf = tmp_path / ".agdt" / "workflows"
        logs = wf / "alice" / "PROJ-1" / "background-tasks" / "logs"
        logs.mkdir(parents=True)
        (logs / "task.log").write_text("data", encoding="utf-8")

        real_iterdir = type(logs).iterdir

        def iterdir_side_effect(self_path):
            if self_path == logs:
                raise PermissionError("access denied")
            return real_iterdir(self_path)

        with patch.object(type(logs), "iterdir", iterdir_side_effect):
            result = scan_identity_logs(tmp_path, "PROJ-1")

        assert result == []

    def test_unsafe_worktree_key_raises(self, tmp_path):
        """Worktree key with path traversal is rejected."""
        with pytest.raises(ValueError, match="not a safe directory segment"):
            scan_identity_logs(tmp_path, "../escape")

    def test_permission_error_on_identity_iterdir_returns_empty(self, tmp_path):
        """PermissionError when iterating identity dirs → empty list."""
        wf = tmp_path / ".agdt" / "workflows"
        wf.mkdir(parents=True)
        (wf / "alice" / "PROJ-1" / "background-tasks" / "logs").mkdir(parents=True)

        with patch.object(type(wf), "iterdir", side_effect=PermissionError("denied")):
            result = scan_identity_logs(tmp_path, "PROJ-1")
        assert result == []

    def test_non_dir_identity_entry_skipped(self, tmp_path):
        """Regular files inside workflows/ are skipped."""
        wf = tmp_path / ".agdt" / "workflows"
        wf.mkdir(parents=True)
        (wf / "some_file.txt").write_text("not a dir", encoding="utf-8")
        logs = wf / "alice" / "PROJ-1" / "background-tasks" / "logs"
        logs.mkdir(parents=True)
        (logs / "task.log").write_text("data", encoding="utf-8")

        result = scan_identity_logs(tmp_path, "PROJ-1")
        assert len(result) == 1
        assert result[0].identity == "alice"

    def test_unsafe_identity_dir_name_skipped(self, tmp_path):
        """Identity dirs with unsafe names are skipped."""
        wf = tmp_path / ".agdt" / "workflows"
        (wf / "alice" / "PROJ-1" / "background-tasks" / "logs").mkdir(parents=True)
        (wf / "alice" / "PROJ-1" / "background-tasks" / "logs" / "task.log").write_text("data", encoding="utf-8")
        # Name with a space is rejected by is_safe_dir_segment
        bad_logs = wf / "bad name" / "PROJ-1" / "background-tasks" / "logs"
        bad_logs.mkdir(parents=True)
        (bad_logs / "task.log").write_text("data", encoding="utf-8")

        result = scan_identity_logs(tmp_path, "PROJ-1")
        assert len(result) == 1
        assert result[0].identity == "alice"

    def test_permission_error_on_log_iterdir_continues(self, tmp_path):
        """PermissionError when iterating log files → identity skipped gracefully."""
        wf = tmp_path / ".agdt" / "workflows"
        logs = wf / "alice" / "PROJ-1" / "background-tasks" / "logs"
        logs.mkdir(parents=True)
        (logs / "task.log").write_text("data", encoding="utf-8")

        original_iterdir = type(logs).iterdir

        def selective_iterdir(path_self):
            if path_self == logs:
                raise PermissionError("denied")
            return original_iterdir(path_self)

        with patch.object(type(logs), "iterdir", autospec=True, side_effect=selective_iterdir):
            result = scan_identity_logs(tmp_path, "PROJ-1")
        assert result == []

    def test_non_file_log_entry_skipped(self, tmp_path):
        """Directories inside logs/ are skipped."""
        wf = tmp_path / ".agdt" / "workflows"
        logs = wf / "alice" / "PROJ-1" / "background-tasks" / "logs"
        logs.mkdir(parents=True)
        (logs / "subdir").mkdir()
        (logs / "task.log").write_text("data", encoding="utf-8")

        result = scan_identity_logs(tmp_path, "PROJ-1")
        assert len(result) == 1
        assert "task.log" in result[0].path.name

    def test_os_error_on_getmtime_skips_log(self, tmp_path):
        """OSError on os.path.getmtime → that log file is skipped."""
        wf = tmp_path / ".agdt" / "workflows"
        logs = wf / "alice" / "PROJ-1" / "background-tasks" / "logs"
        logs.mkdir(parents=True)
        (logs / "task.log").write_text("data", encoding="utf-8")

        with patch("os.path.getmtime", side_effect=OSError("cannot stat")):
            result = scan_identity_logs(tmp_path, "PROJ-1")
        assert result == []
