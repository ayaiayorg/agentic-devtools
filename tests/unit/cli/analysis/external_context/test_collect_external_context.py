"""Tests for collect_external_context()."""

from __future__ import annotations

from unittest.mock import patch

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
        """External worktree without matching worktree_key logs → None."""
        wt_path = tmp_path / "ext-worktree"
        wt_logs = wt_path / ".agdt" / "workflows" / "alice" / "OTHER-KEY" / "background-tasks" / "logs"
        wt_logs.mkdir(parents=True)
        (wt_logs / "task.log").write_text("log content", encoding="utf-8")

        with patch(
            "agentic_devtools.cli.analysis.external_context._discover_worktrees",
            return_value=[str(wt_path)],
        ):
            result = collect_external_context(tmp_path, "PROJ-1")

        assert result is None

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
