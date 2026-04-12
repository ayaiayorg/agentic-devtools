"""Tests for scan_identity_logs()."""

from __future__ import annotations

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
