"""Tests for GetCurrentGitBranch."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.preflight import (
    get_current_git_branch,
)


class TestGetCurrentGitBranch:
    """Tests for get_current_git_branch function."""

    def test_returns_branch_name(self):
        """Test that it returns the branch name on success."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "feature/DFLY-1234/test\n"

            result = get_current_git_branch()
            assert result == "feature/DFLY-1234/test"

    def test_returns_none_on_failure(self):
        """Test that it returns None on subprocess failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1

            result = get_current_git_branch()
            assert result is None

    def test_returns_none_on_empty_output(self):
        """Test that it returns None when no branch (detached HEAD)."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""

            result = get_current_git_branch()
            assert result is None

    def test_handles_file_not_found(self):
        """Test that it handles git not being installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = get_current_git_branch()
            assert result is None
