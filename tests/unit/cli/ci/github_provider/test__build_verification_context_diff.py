"""Tests for _build_verification_context_diff()."""

from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


class TestBuildVerificationContextDiff:
    """Tests for _build_verification_context_diff edge cases."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_returns_empty_on_exception(self, mock_run_safe) -> None:
        mock_run_safe.side_effect = RuntimeError("git not found")
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider._build_verification_context_diff("review_sha", "head_sha")

        assert result == ""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_truncates_large_diff(self, mock_run_safe) -> None:
        class _Result:
            returncode = 0
            stdout = "x" * 20000
            stderr = ""

        mock_run_safe.return_value = _Result()
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider._build_verification_context_diff("review_sha", "head_sha")

        assert len(result) == 16000
