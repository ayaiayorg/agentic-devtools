"""Tests for _repo_from_git_remote helper."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.github.repo_resolution import _resolve_repo_from_git_remote as _repo_from_git_remote

MODULE = "agentic_devtools.cli.github.repo_resolution"


class TestRepoFromGitRemote:
    """Tests for _repo_from_git_remote."""

    @patch(f"{MODULE}.run_safe")
    def test_https_url_parsed(self, mock_run):
        """Extracts owner/repo from HTTPS remote URL."""
        mock_run.return_value = MagicMock(returncode=0, stdout="https://github.com/myowner/myrepo.git\n")
        assert _repo_from_git_remote() == "myowner/myrepo"

    @patch(f"{MODULE}.run_safe")
    def test_ssh_url_parsed(self, mock_run):
        """Extracts owner/repo from SSH remote URL."""
        mock_run.return_value = MagicMock(returncode=0, stdout="git@github.com:myowner/myrepo.git\n")
        assert _repo_from_git_remote() == "myowner/myrepo"

    @patch(f"{MODULE}.run_safe")
    def test_https_url_without_git_suffix(self, mock_run):
        """Extracts owner/repo from HTTPS URL without .git suffix."""
        mock_run.return_value = MagicMock(returncode=0, stdout="https://github.com/myowner/myrepo\n")
        assert _repo_from_git_remote() == "myowner/myrepo"

    @patch(f"{MODULE}.run_safe")
    def test_non_github_url_returns_none(self, mock_run):
        """Returns None for non-GitHub remote URL."""
        mock_run.return_value = MagicMock(returncode=0, stdout="https://gitlab.com/owner/repo.git\n")
        assert _repo_from_git_remote() is None

    @patch(f"{MODULE}.run_safe")
    def test_git_failure_returns_none(self, mock_run):
        """Returns None when git command fails."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
        assert _repo_from_git_remote() is None

    @patch(f"{MODULE}.run_safe", side_effect=OSError("git not found"))
    def test_os_error_returns_none(self, mock_run):
        """Returns None on OSError."""
        assert _repo_from_git_remote() is None

    @patch(f"{MODULE}.run_safe")
    def test_empty_stdout_returns_none(self, mock_run):
        """Returns None when stdout is empty."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        assert _repo_from_git_remote() is None
