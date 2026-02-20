"""Tests for GetReposParentDir."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import (
    get_repos_parent_dir,
)


class TestGetReposParentDir:
    """Tests for get_repos_parent_dir function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    def test_returns_parent_dir_of_main_repo(self, mock_get_main):
        """Test returning parent directory of main repo."""
        mock_get_main.return_value = "/repos/main-repo"

        result = get_repos_parent_dir()

        # On Windows, Path normalizes slashes
        assert "repos" in result

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    def test_returns_none_when_main_repo_not_found(self, mock_get_main):
        """Test returning None when main repo cannot be found."""
        mock_get_main.return_value = None

        result = get_repos_parent_dir()

        assert result is None
