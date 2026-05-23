"""Tests for GitHubActionsProvider.get_commit_range_diff()."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agentic_devtools.cli.ci.exceptions import ProviderRateLimitError
from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


def _mock_run_safe_result(*, returncode: int, stdout: str = "", stderr: str = ""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


class TestGetCommitRangeDiff:
    """Tests for commit-range diff retrieval."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_returns_stdout_on_success(self, mock_run_safe):
        mock_run_safe.return_value = _mock_run_safe_result(returncode=0, stdout="diff --git a/x b/x")
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.get_commit_range_diff("abc", "def")

        assert result == "diff --git a/x b/x"
        mock_run_safe.assert_called_once_with(
            [
                "gh",
                "api",
                "/repos/owner/repo/compare/abc...def",
                "--method",
                "GET",
                "-H",
                "Accept: application/vnd.github.v3.diff",
            ],
            capture_output=True,
            text=True,
            shell=False,
        )

    @patch("agentic_devtools.cli.ci.retry.time.sleep")
    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_raises_provider_rate_limit_error_on_transient_failure(self, mock_run_safe, _mock_sleep):
        mock_run_safe.return_value = _mock_run_safe_result(
            returncode=1,
            stderr="HTTP 503 service unavailable",
        )
        provider = GitHubActionsProvider(repo="owner/repo")

        with pytest.raises(ProviderRateLimitError):
            provider.get_commit_range_diff("abc", "def")

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_raises_runtime_error_on_non_transient_failure(self, mock_run_safe):
        mock_run_safe.return_value = _mock_run_safe_result(returncode=1, stderr="boom")
        provider = GitHubActionsProvider(repo="owner/repo")

        with pytest.raises(RuntimeError, match="gh api compare diff failed: boom"):
            provider.get_commit_range_diff("abc", "def")
