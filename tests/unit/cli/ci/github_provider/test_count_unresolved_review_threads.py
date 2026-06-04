"""Tests for GitHubActionsProvider.count_unresolved_review_threads()."""

import json
from unittest.mock import patch

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider


def _mock_run_safe_response(data):
    class _Result:
        returncode = 0
        stdout = json.dumps(data)
        stderr = ""

    return _Result()


def _graphql_response(nodes, has_next_page=False, end_cursor=None):
    """Build a minimal GraphQL response for review threads."""
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "pageInfo": {"hasNextPage": has_next_page, "endCursor": end_cursor},
                        "nodes": nodes,
                    }
                }
            }
        }
    }


class TestCountUnresolvedReviewThreads:
    """Tests for count_unresolved_review_threads."""

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_zero_threads_returns_zero(self, mock_run_safe):
        """No review threads → 0 unresolved."""
        mock_run_safe.return_value = _mock_run_safe_response(_graphql_response([]))
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.count_unresolved_review_threads(42)

        assert result == 0

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_all_resolved_returns_zero(self, mock_run_safe):
        """All threads resolved → 0 unresolved."""
        nodes = [
            {"id": "t1", "isResolved": True, "comments": {"nodes": [{"databaseId": 1}]}},
            {"id": "t2", "isResolved": True, "comments": {"nodes": [{"databaseId": 2}]}},
        ]
        mock_run_safe.return_value = _mock_run_safe_response(_graphql_response(nodes))
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.count_unresolved_review_threads(42)

        assert result == 0

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_mix_returns_correct_count(self, mock_run_safe):
        """Mix of resolved and unresolved → correct unresolved count."""
        nodes = [
            {"id": "t1", "isResolved": True, "comments": {"nodes": [{"databaseId": 1}]}},
            {"id": "t2", "isResolved": False, "comments": {"nodes": [{"databaseId": 2}]}},
            {"id": "t3", "isResolved": False, "comments": {"nodes": [{"databaseId": 3}]}},
        ]
        mock_run_safe.return_value = _mock_run_safe_response(_graphql_response(nodes))
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.count_unresolved_review_threads(42)

        assert result == 2

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_pagination_accumulates(self, mock_run_safe):
        """Pagination across multiple pages accumulates unresolved count."""
        page1 = _graphql_response(
            [{"id": "t1", "isResolved": False, "comments": {"nodes": [{"databaseId": 1}]}}],
            has_next_page=True,
            end_cursor="cursor1",
        )
        page2 = _graphql_response(
            [{"id": "t2", "isResolved": False, "comments": {"nodes": [{"databaseId": 2}]}}],
            has_next_page=False,
        )
        mock_run_safe.side_effect = [
            _mock_run_safe_response(page1),
            _mock_run_safe_response(page2),
        ]
        provider = GitHubActionsProvider(repo="owner/repo")

        result = provider.count_unresolved_review_threads(42)

        assert result == 2

    @patch("agentic_devtools.cli.ci.github_provider.run_safe")
    def test_api_failure_propagates_exception(self, mock_run_safe):
        """API failure propagates as exception (not swallowed)."""
        mock_run_safe.side_effect = RuntimeError("API error")
        provider = GitHubActionsProvider(repo="owner/repo")

        import pytest

        with pytest.raises(RuntimeError, match="API error"):
            provider.count_unresolved_review_threads(42)
