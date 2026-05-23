"""Tests for GitHubActionsProvider.get_pr_diff()."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agentic_devtools.cli.ci.exceptions import ProviderRateLimitError
from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


def _mock_run_safe_result(*, returncode: int, stdout: str = "", stderr: str = ""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


class TestGetPrDiff:
    """Tests for PR diff retrieval."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_returns_stdout_on_success(self, mock_run_safe):
        mock_run_safe.return_value = _mock_run_safe_result(returncode=0, stdout="diff --git a/x b/x")
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.get_pr_diff(42)

        assert result == "diff --git a/x b/x"
        mock_run_safe.assert_called_once_with(
            ["gh", "pr", "diff", "42", "--repo", "owner/repo"],
            capture_output=True,
            text=True,
            shell=False,
        )

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_raises_runtime_error_on_failure(self, mock_run_safe):
        mock_run_safe.return_value = _mock_run_safe_result(returncode=1, stderr="boom")
        provider = GitHubActionsProvider(repo="owner/repo")

        with pytest.raises(RuntimeError, match="gh pr diff failed: boom"):
            provider.get_pr_diff(42)

    @patch("agentic_devtools.cli.ci.retry.time.sleep")
    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_raises_provider_rate_limit_error_on_transient_failure(self, mock_run_safe, _mock_sleep):
        mock_run_safe.return_value = _mock_run_safe_result(returncode=1, stderr="HTTP 503 service unavailable")
        provider = GitHubActionsProvider(repo="owner/repo")

        with pytest.raises(ProviderRateLimitError):
            provider.get_pr_diff(42)

    @patch("agentic_devtools.cli.ci.retry.time.sleep")
    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_raises_provider_rate_limit_error_on_rate_limit_phrase(self, mock_run_safe, _mock_sleep):
        mock_run_safe.return_value = _mock_run_safe_result(
            returncode=1,
            stderr="secondary rate limit exceeded",
        )
        provider = GitHubActionsProvider(repo="owner/repo")

        with pytest.raises(ProviderRateLimitError):
            provider.get_pr_diff(42)

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_non_status_numbers_in_stderr_remain_non_retryable(self, mock_run_safe):
        mock_run_safe.return_value = _mock_run_safe_result(returncode=1, stderr="line 429 failed")
        provider = GitHubActionsProvider(repo="owner/repo")

        with pytest.raises(RuntimeError, match="gh pr diff failed: line 429 failed"):
            provider.get_pr_diff(42)
