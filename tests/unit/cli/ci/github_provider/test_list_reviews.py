"""Tests for GitHubActionsProvider.list_reviews() method."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.models import ReviewInfo


def _mock_run_safe_response(data):
    class _Result:
        returncode = 0
        stdout = json.dumps(data)
        stderr = ""

    return _Result()


class TestListReviews:
    """Tests for GitHubActionsProvider.list_reviews()."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_returns_reviews(self, mock_run_safe) -> None:
        mock_run_safe.return_value = _mock_run_safe_response(
            [
                {"id": 1, "user": {"login": "reviewer1"}, "state": "APPROVED", "body": "LGTM"},
                {"id": 2, "user": {"login": "bot"}, "state": "COMMENTED", "body": None},
            ]
        )

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.list_reviews(42)

        assert len(result) == 2
        assert isinstance(result[0], ReviewInfo)
        assert result[0].user == "reviewer1"
        assert result[0].state == "APPROVED"
        assert result[1].body == ""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_empty_reviews(self, mock_run_safe) -> None:
        mock_run_safe.return_value = _mock_run_safe_response([])

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.list_reviews(1)

        assert result == []
