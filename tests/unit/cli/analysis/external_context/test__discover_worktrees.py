"""Tests for _discover_worktrees()."""

from __future__ import annotations

from unittest.mock import patch

from agentic_devtools.cli.analysis.external_context import _discover_worktrees


class TestDiscoverWorktrees:
    """Tests for discovering git worktrees."""

    def test_no_git_command_returns_empty(self, tmp_path):
        """FileNotFoundError when git is missing → empty list."""
        with patch(
            "agentic_devtools.cli.analysis.external_context.subprocess.run",
            side_effect=FileNotFoundError("git not found"),
        ):
            result = _discover_worktrees(tmp_path)
        assert result == []

    def test_os_error_returns_empty(self, tmp_path):
        """OSError during subprocess → empty list."""
        with patch(
            "agentic_devtools.cli.analysis.external_context.subprocess.run",
            side_effect=OSError("some error"),
        ):
            result = _discover_worktrees(tmp_path)
        assert result == []

    def test_nonzero_returncode_returns_empty(self, tmp_path):
        """Non-zero return code from git → empty list."""
        mock_result = type("Result", (), {"returncode": 1, "stdout": ""})()
        with patch(
            "agentic_devtools.cli.analysis.external_context.subprocess.run",
            return_value=mock_result,
        ):
            result = _discover_worktrees(tmp_path)
        assert result == []

    def test_excludes_main_worktree(self, tmp_path):
        """Main worktree (at git_root) is excluded from results."""
        resolved = str(tmp_path.resolve())
        porcelain = f"worktree {resolved}\nHEAD abc123\nbranch refs/heads/main\n"
        mock_result = type("Result", (), {"returncode": 0, "stdout": porcelain})()
        with patch(
            "agentic_devtools.cli.analysis.external_context.subprocess.run",
            return_value=mock_result,
        ):
            result = _discover_worktrees(tmp_path)
        assert result == []

    def test_returns_external_worktrees_sorted(self, tmp_path):
        """External worktrees are returned sorted."""
        resolved = str(tmp_path.resolve())
        wt_b = str(tmp_path.resolve() / "wt-b")
        wt_a = str(tmp_path.resolve() / "wt-a")
        porcelain = (
            f"worktree {resolved}\n"
            f"HEAD abc123\n"
            f"branch refs/heads/main\n"
            f"\n"
            f"worktree {wt_b}\n"
            f"HEAD def456\n"
            f"branch refs/heads/feature-b\n"
            f"\n"
            f"worktree {wt_a}\n"
            f"HEAD ghi789\n"
            f"branch refs/heads/feature-a\n"
        )
        mock_result = type("Result", (), {"returncode": 0, "stdout": porcelain})()
        with patch(
            "agentic_devtools.cli.analysis.external_context.subprocess.run",
            return_value=mock_result,
        ):
            result = _discover_worktrees(tmp_path)
        assert result == [wt_a, wt_b]

    def test_empty_worktree_path_skipped(self, tmp_path):
        """Empty worktree path line is skipped."""
        porcelain = "worktree \nHEAD abc123\n"
        mock_result = type("Result", (), {"returncode": 0, "stdout": porcelain})()
        with patch(
            "agentic_devtools.cli.analysis.external_context.subprocess.run",
            return_value=mock_result,
        ):
            result = _discover_worktrees(tmp_path)
        assert result == []

    def test_relative_worktree_path_resolved_against_git_root(self, tmp_path):
        """Relative worktree paths are resolved relative to git_root."""
        resolved_main = str(tmp_path.resolve())
        # Relative path that resolves to something different from main
        porcelain = f"worktree {resolved_main}\nHEAD abc123\n\nworktree relative-wt\nHEAD def456\n"
        mock_result = type("Result", (), {"returncode": 0, "stdout": porcelain})()
        with patch(
            "agentic_devtools.cli.analysis.external_context.subprocess.run",
            return_value=mock_result,
        ):
            result = _discover_worktrees(tmp_path)
        expected = str((tmp_path / "relative-wt").resolve())
        assert result == [expected]
