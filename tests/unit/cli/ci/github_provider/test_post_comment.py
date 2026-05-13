"""Tests for GitHubActionsProvider.post_comment() method."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


def _mock_run_safe_response(data):
    class _Result:
        returncode = 0
        stdout = json.dumps(data)
        stderr = ""

    return _Result()


class TestPostComment:
    """Tests for GitHubActionsProvider.post_comment()."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_returns_comment_id(self, mock_run_safe) -> None:
        mock_run_safe.return_value = _mock_run_safe_response({"id": 12345, "body": "hello"})

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.post_comment(42, "hello")

        assert result == 12345

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_sends_body_in_request(self, mock_run_safe) -> None:
        mock_run_safe.return_value = _mock_run_safe_response({"id": 1})

        provider = GitHubActionsProvider(repo="owner/repo")
        provider.post_comment(1, "test body")

        kwargs = mock_run_safe.call_args[1]
        assert kwargs.get("input") is not None
        body = json.loads(kwargs["input"])
        assert body == {"body": "test body"}
