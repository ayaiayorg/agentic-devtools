"""Tests for fetch_applicable_suggestions function."""

import os
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.ci.pipeline.suggestions import fetch_applicable_suggestions
from agentic_devtools.cli.ci.retry import RetryableError


def _make_provider(responses: list[dict]) -> MagicMock:
    """Create a mock provider with pre-configured GraphQL responses."""
    provider = MagicMock()
    provider._repo = "owner/repo"
    provider.graphql.side_effect = responses
    return provider


def _build_graphql_response(
    threads: list[dict | None],
    *,
    has_next_page: bool = False,
    end_cursor: str | None = None,
    pr_node_id: str = "PR_NODE_1",
) -> dict:
    """Build a GraphQL response with given threads."""
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "id": pr_node_id,
                    "reviewThreads": {
                        "pageInfo": {
                            "hasNextPage": has_next_page,
                            "endCursor": end_cursor,
                        },
                        "nodes": threads,
                    },
                }
            }
        }
    }


def _make_thread(
    thread_id: str,
    *,
    is_resolved: bool = False,
    comments: list[dict] | None = None,
) -> dict:
    """Build a thread node."""
    return {
        "id": thread_id,
        "isResolved": is_resolved,
        "comments": {"nodes": comments or []},
    }


def _make_comment(
    database_id: int,
    suggestions: list[dict] | None = None,
) -> dict:
    """Build a comment node."""
    return {
        "databaseId": database_id,
        "suggestedChanges": {"nodes": suggestions or []},
    }


def _make_suggestion(suggestion_id: str, *, outdated: bool = False) -> dict:
    """Build a suggestion node."""
    return {"id": suggestion_id, "outdated": outdated}


class TestFetchApplicableSuggestions:
    """Tests for fetch_applicable_suggestions."""

    def test_empty_result(self) -> None:
        """No threads returns empty list."""
        provider = _make_provider([_build_graphql_response([])])
        suggestions, pr_id = fetch_applicable_suggestions(provider, 42)
        assert suggestions == []
        assert pr_id == "PR_NODE_1"

    def test_query_requests_suggested_changes_with_pagination(self) -> None:
        """GraphQL query includes required pagination arg for suggestedChanges."""
        provider = _make_provider([_build_graphql_response([])])
        fetch_applicable_suggestions(provider, 42)
        query = provider.graphql.call_args.kwargs["query"]
        assert "suggestedChanges(first: 100)" in query

    def test_filters_outdated_suggestions(self) -> None:
        """Outdated suggestions are excluded."""
        thread = _make_thread(
            "T1",
            comments=[
                _make_comment(
                    100,
                    [
                        _make_suggestion("SC1", outdated=True),
                        _make_suggestion("SC2", outdated=False),
                    ],
                ),
            ],
        )
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 1
        assert suggestions[0].suggestion_id == "SC2"
        assert suggestions[0].comment_database_id == 100

    def test_skips_resolved_threads(self) -> None:
        """Resolved threads are skipped entirely."""
        thread = _make_thread(
            "T1",
            is_resolved=True,
            comments=[
                _make_comment(100, [_make_suggestion("SC1")]),
            ],
        )
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert suggestions == []

    def test_pagination(self) -> None:
        """Handles multiple pages of threads."""
        thread1 = _make_thread(
            "T1",
            comments=[_make_comment(100, [_make_suggestion("SC1")])],
        )
        thread2 = _make_thread(
            "T2",
            comments=[_make_comment(200, [_make_suggestion("SC2")])],
        )
        provider = _make_provider(
            [
                _build_graphql_response([thread1], has_next_page=True, end_cursor="cursor1"),
                _build_graphql_response([thread2]),
            ]
        )
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 2
        assert suggestions[0].suggestion_id == "SC1"
        assert suggestions[1].suggestion_id == "SC2"

    def test_multiple_suggestions_per_comment(self) -> None:
        """Multiple suggestions in a single comment are all returned."""
        thread = _make_thread(
            "T1",
            comments=[
                _make_comment(
                    100,
                    [
                        _make_suggestion("SC1"),
                        _make_suggestion("SC2"),
                    ],
                ),
            ],
        )
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 2
        assert all(s.comment_database_id == 100 for s in suggestions)

    def test_raises_when_repo_not_determinable(self) -> None:
        """RuntimeError when provider has no _repo and GITHUB_REPOSITORY is unset."""
        provider = MagicMock()
        provider._repo = ""

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="Cannot determine repository"):
                fetch_applicable_suggestions(provider, 1)

    def test_raises_runtime_error_on_graphql_errors(self) -> None:
        """Non-transient GraphQL errors raise RuntimeError."""
        provider = _make_provider(
            [
                {
                    "errors": [{"message": "Could not resolve to a PullRequest with the number of 9999"}],
                }
            ]
        )

        with pytest.raises(RuntimeError, match="GraphQL query failed"):
            fetch_applicable_suggestions(provider, 9999)

    def test_raises_runtime_error_when_pull_request_node_is_null(self) -> None:
        """Null pullRequest node raises a deterministic RuntimeError."""
        provider = _make_provider(
            [
                {
                    "data": {
                        "repository": {
                            "pullRequest": None,
                        }
                    }
                }
            ]
        )

        with pytest.raises(RuntimeError, match="pullRequest is null or invalid in GraphQL response"):
            fetch_applicable_suggestions(provider, 42)

    def test_raises_retryable_error_on_graphql_rate_limit_error(self) -> None:
        """Rate-limit GraphQL errors raise RetryableError."""
        provider = _make_provider(
            [
                {
                    "errors": [{"message": "You have exceeded a secondary rate limit. Please wait a few minutes."}],
                }
            ]
        )

        with pytest.raises(RetryableError, match="Transient GraphQL query error"):
            fetch_applicable_suggestions(provider, 42)

    def test_null_thread_node_is_skipped(self) -> None:
        """Null entries in reviewThreads.nodes are skipped without error."""
        valid_thread = _make_thread(
            "T1",
            comments=[_make_comment(100, [_make_suggestion("SC1")])],
        )
        response = _build_graphql_response([None, valid_thread])
        provider = _make_provider([response])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 1
        assert suggestions[0].suggestion_id == "SC1"

    def test_null_comment_node_is_skipped(self) -> None:
        """Null entries in comments.nodes are skipped without error."""
        valid_comment = _make_comment(200, [_make_suggestion("SC2")])
        thread = {
            "id": "T1",
            "isResolved": False,
            "comments": {"nodes": [None, valid_comment]},
        }
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 1
        assert suggestions[0].suggestion_id == "SC2"

    def test_null_suggestion_node_is_skipped(self) -> None:
        """Null entries in suggestedChanges.nodes are skipped without error."""
        comment = {
            "databaseId": 300,
            "suggestedChanges": {"nodes": [None, {"id": "SC3", "outdated": False}]},
        }
        thread = {"id": "T1", "isResolved": False, "comments": {"nodes": [comment]}}
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 1
        assert suggestions[0].suggestion_id == "SC3"

    def test_suggestion_without_id_is_skipped(self) -> None:
        """Suggestion entries missing an 'id' field are skipped without error."""
        comment = {
            "databaseId": 400,
            "suggestedChanges": {
                "nodes": [
                    {"outdated": False},
                    {"id": "SC4", "outdated": False},
                ]
            },
        }
        thread = {"id": "T1", "isResolved": False, "comments": {"nodes": [comment]}}
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 1
        assert suggestions[0].suggestion_id == "SC4"

    def test_null_review_threads_value_is_handled(self) -> None:
        """Explicit null for reviewThreads in response yields empty suggestions."""
        response = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "id": "PR_NODE_X",
                        "reviewThreads": None,
                    }
                }
            }
        }
        provider = _make_provider([response])
        suggestions, pr_id = fetch_applicable_suggestions(provider, 1)
        assert suggestions == []
        assert pr_id == "PR_NODE_X"

    def test_non_int_database_id_defaults_to_zero(self) -> None:
        """Non-int databaseId values are coerced to 0 rather than leaking."""
        comment = {
            "databaseId": "not-an-int",
            "suggestedChanges": {"nodes": [{"id": "SC5", "outdated": False}]},
        }
        thread = {"id": "T1", "isResolved": False, "comments": {"nodes": [comment]}}
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 1
        assert suggestions[0].comment_database_id == 0

    def test_none_database_id_defaults_to_zero(self) -> None:
        """Explicit null databaseId is coerced to 0 rather than leaking."""
        comment = {
            "databaseId": None,
            "suggestedChanges": {"nodes": [{"id": "SC6", "outdated": False}]},
        }
        thread = {"id": "T1", "isResolved": False, "comments": {"nodes": [comment]}}
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 1
        assert suggestions[0].comment_database_id == 0

    def test_has_next_page_with_null_cursor_stops_pagination(self) -> None:
        """hasNextPage=True with null endCursor stops pagination rather than looping."""
        thread = _make_thread(
            "T1",
            comments=[_make_comment(100, [_make_suggestion("SC1")])],
        )
        response = _build_graphql_response([thread], has_next_page=True, end_cursor=None)
        provider = _make_provider([response])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        # Should not loop: only the first page is consumed
        assert provider.graphql.call_count == 1
        assert len(suggestions) == 1
        assert suggestions[0].suggestion_id == "SC1"
