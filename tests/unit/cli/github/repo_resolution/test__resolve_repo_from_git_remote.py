"""Tests for _resolve_repo_from_git_remote."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.github.repo_resolution import _resolve_repo_from_git_remote

_MOD = "agentic_devtools.cli.github.repo_resolution"


class TestResolveRepoFromGitRemote:
    """Tests for _resolve_repo_from_git_remote."""

    @patch(f"{_MOD}.run_safe")
    def test_https_url(self, mock_run):
        """Parses owner/repo from HTTPS URL."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/myorg/myrepo.git\n",
        )

        result = _resolve_repo_from_git_remote()

        assert result == "myorg/myrepo"

    @patch(f"{_MOD}.run_safe")
    def test_ssh_url(self, mock_run):
        """Parses owner/repo from SSH URL."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="git@github.com:myorg/myrepo.git\n",
        )

        result = _resolve_repo_from_git_remote()

        assert result == "myorg/myrepo"

    @patch(f"{_MOD}.run_safe")
    def test_non_zero_exit(self, mock_run):
        """Returns None on non-zero exit code."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        result = _resolve_repo_from_git_remote()

        assert result is None

    @patch(f"{_MOD}.run_safe")
    def test_empty_stdout(self, mock_run):
        """Returns None on empty stdout."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        result = _resolve_repo_from_git_remote()

        assert result is None

    @patch(f"{_MOD}.run_safe", side_effect=OSError("git not found"))
    def test_oserror(self, mock_run):
        """Returns None when git command raises OSError."""
        result = _resolve_repo_from_git_remote()

        assert result is None

    @patch(f"{_MOD}.run_safe")
    def test_non_github_url(self, mock_run):
        """Returns None for non-GitHub remote URL."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://dev.azure.com/org/project/_git/repo\n",
        )

        result = _resolve_repo_from_git_remote()

        assert result is None

    @patch(f"{_MOD}.run_safe")
    def test_https_url_without_git_suffix(self, mock_run):
        """Parses HTTPS URL without .git suffix."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/owner/repo\n",
        )

        result = _resolve_repo_from_git_remote()

        assert result == "owner/repo"
