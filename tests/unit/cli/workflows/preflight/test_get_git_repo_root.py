"""Tests for GetGitRepoRoot."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.preflight import (
    get_git_repo_root,
)


class TestGetGitRepoRoot:
    """Tests for get_git_repo_root function."""

    def test_returns_repo_root(self):
        """Test that it returns the repo root path."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "/home/user/repos/my-repo\n"

            result = get_git_repo_root()
            assert result == "/home/user/repos/my-repo"

    def test_returns_none_on_failure(self):
        """Test that it returns None outside a git repo."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 128

            result = get_git_repo_root()
            assert result is None
