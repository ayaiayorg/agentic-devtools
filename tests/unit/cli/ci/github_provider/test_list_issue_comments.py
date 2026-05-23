"""Tests for GitHubActionsProvider.list_issue_comments()."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.models import IssueCommentInfo


def _mock_run_safe_response(data):
    class _Result:
        returncode = 0
        stdout = json.dumps(data)
        stderr = ""

    return _Result()


class TestListIssueComments:
    """Tests for listing PR issue comments."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_returns_issue_comment_info_objects(self, mock_run_safe):
        mock_run_safe.return_value = _mock_run_safe_response(
            [
                {
                    "id": 11,
                    "body": "first",
                    "created_at": "2026-01-01T00:00:00Z",
                    "user": {"login": "dev"},
                },
                {
                    "id": 12,
                    "body": "second",
                    "created_at": "2026-01-02T00:00:00Z",
                    "user": {"login": "copilot[bot]"},
                },
            ]
        )
        provider = GitHubActionsProvider(repo="owner/repo")

        comments = provider.list_issue_comments(42)

        assert comments == [
            IssueCommentInfo(id=11, author="dev", body="first", created_at="2026-01-01T00:00:00Z"),
            IssueCommentInfo(
                id=12,
                author="copilot[bot]",
                body="second",
                created_at="2026-01-02T00:00:00Z",
            ),
        ]

