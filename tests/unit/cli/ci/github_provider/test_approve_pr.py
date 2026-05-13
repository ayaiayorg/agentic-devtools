"""Tests for GitHubActionsProvider.approve_pr() method."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


class TestApprovePR:
    """Tests for GitHubActionsProvider.approve_pr()."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_approve_pr_posts_review(self, mock_run_safe) -> None:
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
