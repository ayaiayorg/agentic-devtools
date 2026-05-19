"""Tests for GitHubActionsProvider.list_review_comments() method."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.models import ReviewCommentInfo


def _mock_run_safe_response(data):
    class _Result:
        returncode = 0
        stdout = json.dumps(data)
        stderr = ""

    return _Result()


class TestListReviewComments:
    """Tests for GitHubActionsProvider.list_review_comments()."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_returns_review_comment_info_objects(self, mock_run_safe) -> None:
        mock_run_safe.return_value = _mock_run_safe_response(
            [
                {
                    "id": 101,
                    "path": "src/foo.py",
                    "body": "Fix the null check",
                    "html_url": "https://github.com/owner/repo/pull/42#pullreviewcomment-101",
                },
                {
                    "id": 202,
                    "path": "src/bar.py",
                    "body": "Add error handling",
                    "html_url": "https://github.com/owner/repo/pull/42#pullreviewcomment-202",
                },
            ]
        )
        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.list_review_comments(42, 7)

        assert len(result) == 2
        assert isinstance(result[0], ReviewCommentInfo)
        assert result[0].id == 101
        assert result[0].path == "src/foo.py"
        assert result[0].body == "Fix the null check"
        assert result[0].html_url == "https://github.com/owner/repo/pull/42#pullreviewcomment-101"
        assert result[0].is_suppressed is False

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_is_suppressed_defaults_to_false(self, mock_run_safe) -> None:
        mock_run_safe.return_value = _mock_run_safe_response(
            [{"id": 1, "path": "f.py", "body": "x", "html_url": "http://x"}]
        )
        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.list_review_comments(1, 1)
        assert result[0].is_suppressed is False

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_is_suppressed_maps_from_minimized_flag(self, mock_run_safe) -> None:
        mock_run_safe.return_value = _mock_run_safe_response(
            [{"id": 2, "path": "f.py", "body": "x", "html_url": "http://x", "is_minimized": True}]
        )
        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.list_review_comments(1, 1)
        assert result[0].is_suppressed is True

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_handles_missing_optional_fields(self, mock_run_safe) -> None:
        """Missing body or html_url fall back to empty string."""
        mock_run_safe.return_value = _mock_run_safe_response([{"id": 5, "path": "foo.py"}])
        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.list_review_comments(10, 20)
        assert len(result) == 1
        assert result[0].body == ""
        assert result[0].html_url == ""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_returns_empty_list_when_no_comments(self, mock_run_safe) -> None:
        mock_run_safe.return_value = _mock_run_safe_response([])
        provider = GitHubActionsProvider(repo="owner/repo")
        result = provider.list_review_comments(42, 7)
        assert result == []
