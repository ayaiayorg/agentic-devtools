"""Tests for _get_git_origin_url in repo_resolution module."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.github import repo_resolution


class TestGetGitOriginUrl:
    """Tests for _get_git_origin_url."""

    def test_returns_url_on_success(self):
        """Returns the stripped stdout on success."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/owner/repo.git\n"

        with patch.object(repo_resolution, "run_safe", return_value=mock_result):
            result = repo_resolution._get_git_origin_url()

        assert result == "https://github.com/owner/repo.git"

    def test_returns_none_on_failure(self):
        """Returns None when git command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch.object(repo_resolution, "run_safe", return_value=mock_result):
            result = repo_resolution._get_git_origin_url()

        assert result is None

    def test_returns_none_on_empty_stdout(self):
        """Returns None when stdout is empty."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "  "

        with patch.object(repo_resolution, "run_safe", return_value=mock_result):
            result = repo_resolution._get_git_origin_url()

        assert result is None

    def test_returns_none_on_file_not_found(self):
        """Returns None when git is not installed."""
        with patch.object(repo_resolution, "run_safe", side_effect=FileNotFoundError):
            result = repo_resolution._get_git_origin_url()

        assert result is None

    def test_uses_shell_false(self):
        """git command must use shell=False."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/owner/repo.git"

        with patch.object(repo_resolution, "run_safe", return_value=mock_result) as mock_run:
            repo_resolution._get_git_origin_url()

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["shell"] is False
