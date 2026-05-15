"""Tests for GitHubActionsProvider.approve_pr() method."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


class TestApprovePR:
    """Tests for GitHubActionsProvider.approve_pr()."""

    @patch.dict("os.environ", {"AGDT_PR_APPROVER_PAT": "ghp_approver_token"})
    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_approve_pr_posts_review_with_approver_token(self, mock_run_safe) -> None:
        class _Result:
            returncode = 0
            stdout = json.dumps({"id": 999})
            stderr = ""

        mock_run_safe.return_value = _Result()

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.approve_pr(42, "abc123", "LGTM!")

        assert result is None
        kwargs = mock_run_safe.call_args[1]
        body = json.loads(kwargs["input"])
        assert body["event"] == "APPROVE"
        assert body["commit_id"] == "abc123"
        assert body["body"] == "LGTM!"
        # Verify the approver token is passed via env
        assert kwargs["env"]["GH_TOKEN"] == "ghp_approver_token"

    @patch.dict("os.environ", {"AGDT_PR_APPROVER_PAT": ""})
    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_approve_pr_skips_when_pat_empty(self, mock_run_safe) -> None:
        """Approval is skipped when AGDT_PR_APPROVER_PAT is empty."""
        provider = GitHubActionsProvider(repo="owner/repo")
        provider.approve_pr(42, "abc123", "LGTM!")

        mock_run_safe.assert_not_called()

    @patch.dict("os.environ", {"AGDT_PR_APPROVER_PAT": "not_present"})
    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_approve_pr_skips_when_pat_missing(self, mock_run_safe) -> None:
        """Approval is skipped when AGDT_PR_APPROVER_PAT is not set."""
        import os

        # Remove the key after patch.dict sets it, simulating unset env var
        del os.environ["AGDT_PR_APPROVER_PAT"]
        provider = GitHubActionsProvider(repo="owner/repo")
        provider.approve_pr(42, "abc123", "LGTM!")

        mock_run_safe.assert_not_called()

    @patch.dict("os.environ", {"AGDT_PR_APPROVER_PAT": "ghp_expired_token"})
    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_approve_pr_handles_401_gracefully(self, mock_run_safe) -> None:
        """Approval is skipped gracefully on 401 (expired/invalid PAT)."""

        class _Result:
            returncode = 1
            stdout = ""
            stderr = "HTTP 401: Bad credentials"

        mock_run_safe.return_value = _Result()

        provider = GitHubActionsProvider(repo="owner/repo")
        # Should not raise
        provider.approve_pr(42, "abc123", "LGTM!")
