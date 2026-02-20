"""Tests for CheckWorktreeExists."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import (
    check_worktree_exists,
)


class TestCheckWorktreeExists:
    """Tests for check_worktree_exists function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("agentic_devtools.cli.workflows.worktree_setup.os.path.exists")
    def test_returns_path_when_worktree_exists(self, mock_exists, mock_parent):
        """Test returning path when worktree exists."""
        mock_parent.return_value = "/repos"
        # First call: worktree path exists, Second call: .git file exists
        mock_exists.side_effect = [True, True]

        result = check_worktree_exists("DFLY-1234")

        assert "DFLY-1234" in result

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("agentic_devtools.cli.workflows.worktree_setup.os.path.exists")
    def test_returns_none_when_worktree_not_exists(self, mock_exists, mock_parent):
        """Test returning None when worktree doesn't exist."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False

        result = check_worktree_exists("DFLY-1234")

        assert result is None

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    def test_returns_none_when_parent_not_found(self, mock_parent):
        """Test returning None when parent directory not found."""
        mock_parent.return_value = None

        result = check_worktree_exists("DFLY-1234")

        assert result is None

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("agentic_devtools.cli.workflows.worktree_setup.os.path.exists")
    def test_returns_none_when_not_valid_git_worktree(self, mock_exists, mock_parent):
        """Test returning None when directory exists but isn't a git worktree."""
        mock_parent.return_value = "/repos"
        # First call: worktree path exists, Second call: .git file doesn't exist
        mock_exists.side_effect = [True, False]

        result = check_worktree_exists("DFLY-1234")

        assert result is None
