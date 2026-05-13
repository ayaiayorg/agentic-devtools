"""Tests for GitHubActionsProvider.find_comment() method."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


def _mock_run_safe_response(data):
    class _Result:
        returncode = 0
        stdout = json.dumps(data)
        stderr = ""

    return _Result()


class TestFindComment:
    """Tests for GitHubActionsProvider.find_comment()."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_finds_comment_with_marker(self, mock_run_safe) -> None:
        mock_run_safe.return_value = _mock_run_safe_response(
            [
                {"id": 1, "body": "normal comment"},
                {"id": 2, "body": "<!-- repair-dispatch:abc:1 --> status update"},
                {"id": 3, "body": "another comment"},
            ]
        )

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.find_comment(42, "<!-- repair-dispatch:")

        assert result is not None
        assert result[0] == 2
        assert "repair-dispatch:abc:1" in result[1]

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_returns_none_when_not_found(self, mock_run_safe) -> None:
        mock_run_safe.return_value = _mock_run_safe_response(
            [
                {"id": 1, "body": "no marker here"},
            ]
        )

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.find_comment(42, "<!-- missing-marker -->")

        assert result is None

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_empty_comments(self, mock_run_safe) -> None:
        mock_run_safe.return_value = _mock_run_safe_response([])

        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.find_comment(1, "marker")

        assert result is None
