"""Tests for IsInWorktree."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.workflows.worktree_setup import (
    is_in_worktree,
)


class TestIsInWorktree:
    """Tests for is_in_worktree function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_true_in_worktree(self, mock_run):
        """Test returns True when in a worktree (git-dir != git-common-dir)."""
        # In a worktree, git-dir points to .git/worktrees/<name>
        # while git-common-dir points to the main repo's .git
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/repos/main/.git/worktrees/DFLY-1234"),
            MagicMock(returncode=0, stdout="/repos/main/.git"),
        ]

        result = is_in_worktree()

        assert result is True

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_false_in_main_repo(self, mock_run):
        """Test returns False when in main repo (git-dir == git-common-dir)."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=".git"),
            MagicMock(returncode=0, stdout=".git"),
        ]

        result = is_in_worktree()

        assert result is False

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_false_on_git_error(self, mock_run):
        """Test returns False when git commands fail."""
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="not a git repo")

        result = is_in_worktree()

        assert result is False

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_false_on_file_not_found(self, mock_run):
        """Test returns False when git is not installed."""
        mock_run.side_effect = FileNotFoundError("git not found")

        result = is_in_worktree()

        assert result is False
