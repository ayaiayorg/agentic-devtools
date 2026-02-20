"""Tests for GetCurrentBranch."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.workflows.worktree_setup import (
    get_current_branch,
)


class TestGetCurrentBranch:
    """Tests for get_current_branch function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_branch_name(self, mock_run):
        """Test returns current branch name."""
        mock_run.return_value = MagicMock(returncode=0, stdout="feature/DFLY-1234/implementation\n")

        result = get_current_branch()

        assert result == "feature/DFLY-1234/implementation"

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_none_on_detached_head(self, mock_run):
        """Test returns None on detached HEAD."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        result = get_current_branch()

        assert result is None

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_none_on_git_error(self, mock_run):
        """Test returns None on git error."""
        mock_run.return_value = MagicMock(returncode=128, stdout="")

        result = get_current_branch()

        assert result is None
