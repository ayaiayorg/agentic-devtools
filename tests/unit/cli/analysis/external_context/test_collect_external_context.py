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
