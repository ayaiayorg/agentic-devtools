"""Tests for retry integration in GitHubActionsProvider."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.ci.exceptions import ProviderRateLimitError
from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


class TestRetryIntegration:
    """Tests verifying provider methods use retry_with_backoff and honor rate limits."""

    @patch("agentic_devtools.cli.ci.retry.time.sleep")
    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_retries_on_rate_limit(self, mock_run_safe, mock_sleep) -> None:
        """Provider raises ProviderRateLimitError after exhausting retries on rate limit."""

        class _RateLimitResult:
            returncode = 1
            stdout = ""
            stderr = "HTTP 429: rate limit exceeded"

        mock_run_safe.return_value = _RateLimitResult()

        provider = GitHubActionsProvider(repo="owner/repo")
        with pytest.raises(ProviderRateLimitError):
            provider.list_pr_files(42)

        # Should have retried (default 5 retries + 1 initial = 6 calls)
        assert mock_run_safe.call_count == 6

    @patch("agentic_devtools.cli.ci.retry.time.sleep")
    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_retries_on_server_error(self, mock_run_safe, mock_sleep) -> None:
        """Provider retries on 500/502/503/504 errors."""

        class _ServerError:
            returncode = 1
            stdout = ""
            stderr = "502 Bad Gateway"

        mock_run_safe.return_value = _ServerError()

        provider = GitHubActionsProvider(repo="owner/repo")
        with pytest.raises(ProviderRateLimitError):
            provider.list_reviews(1)

        assert mock_run_safe.call_count == 6

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_non_retryable_error_propagates(self, mock_run_safe) -> None:
        """Non-retryable errors (e.g., 404) propagate immediately."""

        class _NotFoundResult:
            returncode = 1
            stdout = ""
            stderr = "HTTP 404: Not Found"

        mock_run_safe.return_value = _NotFoundResult()

        provider = GitHubActionsProvider(repo="owner/repo")
        with pytest.raises(RuntimeError, match="GitHub API error"):
            provider.list_pr_files(999)

        assert mock_run_safe.call_count == 1
