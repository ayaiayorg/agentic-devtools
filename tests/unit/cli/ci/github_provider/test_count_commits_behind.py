"""Tests for GitHubActionsProvider.count_commits_behind."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


class TestCountCommitsBehind:
    """Tests for count_commits_behind method."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_returns_count_on_success(self, mock_run_safe) -> None:
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="3\n", stderr="")
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.count_commits_behind(pr_number=1, base_branch="main", head_branch="feature")

        assert result == 3
        mock_run_safe.assert_called_once()
        call_args = mock_run_safe.call_args[0][0]
        assert any("/repos/owner/repo/compare/main...feature" in arg for arg in call_args)
        assert ".behind_by" in call_args

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_url_encodes_branch_names(self, mock_run_safe) -> None:
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="3\n", stderr="")
        provider = GitHubActionsProvider(repo="owner/repo")

        provider.count_commits_behind(pr_number=1, base_branch="release/v1", head_branch="feature/foo")

        call_args = mock_run_safe.call_args[0][0]
        assert any("/repos/owner/repo/compare/release%2Fv1...feature%2Ffoo" in arg for arg in call_args)

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_raises_on_nonzero_returncode(self, mock_run_safe) -> None:
        mock_run_safe.return_value = MagicMock(returncode=1, stdout="", stderr="not found")
        provider = GitHubActionsProvider(repo="owner/repo")

        with pytest.raises(RuntimeError, match="PR #1: compare API failed: not found"):
            provider.count_commits_behind(pr_number=1, base_branch="main", head_branch="feature")

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_raises_on_exception(self, mock_run_safe) -> None:
        mock_run_safe.side_effect = RuntimeError("network error")
        provider = GitHubActionsProvider(repo="owner/repo")

        with pytest.raises(RuntimeError, match="PR #1: compare API request failed"):
            provider.count_commits_behind(pr_number=1, base_branch="main", head_branch="feature")

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_returns_zero_on_empty_stdout(self, mock_run_safe) -> None:
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="", stderr="")
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.count_commits_behind(pr_number=1, base_branch="main", head_branch="feature")

        assert result == 0
