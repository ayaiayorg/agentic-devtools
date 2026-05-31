"""Tests for GitHubActionsProvider.publish_pr() method."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


class TestPublishPR:
    """Tests for GitHubActionsProvider.publish_pr()."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_publish_pr_calls_gh_pr_ready(self, mock_run_safe) -> None:
        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""

        mock_run_safe.return_value = _Result()

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.publish_pr(42)

        assert result is None
        args = mock_run_safe.call_args[0][0]
        assert args == ["gh", "pr", "ready", "42", "--repo", "owner/repo"]

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_publish_pr_uses_stdout_when_stderr_empty(self, mock_run_safe) -> None:
        class _Result:
            returncode = 1
            stdout = "gh error from stdout"
            stderr = ""

        mock_run_safe.return_value = _Result()

        provider = GitHubActionsProvider(repo="owner/repo")

        with pytest.raises(RuntimeError, match="gh error from stdout"):
            provider.publish_pr(42)

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_publish_pr_without_repo_omits_repo_flag(self, mock_run_safe) -> None:
        class _Result:
            returncode = 0
            stdout = ""
            stderr = ""

        mock_run_safe.return_value = _Result()

        provider = GitHubActionsProvider(repo="")
        provider.publish_pr(7)

        args = mock_run_safe.call_args[0][0]
        assert "--repo" not in args
        assert args == ["gh", "pr", "ready", "7"]
