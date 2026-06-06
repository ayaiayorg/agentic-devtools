"""Tests for fetch_applicable_suggestions function."""

import logging
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
    head_ref_name: str = "feature-branch",
    head_ref_oid: str = "abc123def456",
) -> dict:
    """Build a GraphQL response with given threads."""
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "id": pr_node_id,
                    "headRefName": head_ref_name,
                    "headRefOid": head_ref_oid,
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


def _build_thread_comments_response(
    comments: list[dict | None],
    *,
    has_next_page: bool = False,
    end_cursor: str | None = None,
) -> dict:
    """Build a GraphQL node() response for paginated thread comments."""
    return {
        "data": {
            "node": {
                "comments": {
                    "pageInfo": {
                        "hasNextPage": has_next_page,
                        "endCursor": end_cursor,
                    },
                    "nodes": comments,
                }
            }
        }
    }


def _make_thread(
    thread_id: str,
    *,
    is_resolved: bool = False,
    is_outdated: bool = False,
    comments: list[dict | None] | None = None,
    comments_has_next_page: bool = False,
    comments_end_cursor: str | None = None,
) -> dict:
    """Build a thread node."""
    return {
        "id": thread_id,
        "isResolved": is_resolved,
        "isOutdated": is_outdated,
        "comments": {
            "pageInfo": {
                "hasNextPage": comments_has_next_page,
                "endCursor": comments_end_cursor,
            },
            "nodes": comments or [],
        },
    }


def _make_comment(
    database_id: int,
    *,
    comment_id: str = "COMMENT_NODE_1",
    body: str = "regular review comment",
    path: str = "src/example.py",
    line: int = 10,
    start_line: int | None = None,
) -> dict:
    """Build a comment node."""
    return {
        "id": comment_id,
        "databaseId": database_id,
        "body": body,
        "path": path,
        "line": line,
        "startLine": start_line,
    }


class TestFetchApplicableSuggestions:
    """Tests for fetch_applicable_suggestions."""

    def test_empty_result(self) -> None:
        """No threads returns empty list."""
        provider = _make_provider([_build_graphql_response([])])
        suggestions, pr_id = fetch_applicable_suggestions(provider, 42)
        assert suggestions == []
        assert pr_id == "PR_NODE_1"

    def test_query_includes_path_and_line_fields(self) -> None:
        """GraphQL query requests path, line, and startLine fields."""
        provider = _make_provider([_build_graphql_response([])])
        fetch_applicable_suggestions(provider, 42)
        query = provider.graphql.call_args.kwargs["query"]
        assert "path" in query
        assert "line" in query
        assert "startLine" in query

    def test_detects_suggestions_from_comment_body_with_path_and_line(self) -> None:
        """Suggestions include path and line range from comment fields."""
        thread = _make_thread(
            "T1",
            comments=[
                _make_comment(
                    100,
                    comment_id="C1",
                    body="```suggestion\nvalue = 1\n```",
                    path="src/main.py",
                    line=15,
                    start_line=14,
                ),
            ],
        )
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 1
        assert suggestions[0].suggestion_id == "C1"
        assert suggestions[0].path == "src/main.py"
        assert suggestions[0].start_line == 14
        assert suggestions[0].end_line == 15
        assert suggestions[0].replacement == "value = 1\n"

    def test_skips_comments_without_path_or_line(self) -> None:
        """Comments with suggestion blocks but missing path/line are skipped."""
        thread = _make_thread(
            "T1",
            comments=[
                _make_comment(
                    100,
                    comment_id="C1",
                    body="```suggestion\nvalue = 1\n```",
                    path="",
                    line=10,
                ),
                _make_comment(
                    101,
                    comment_id="C2",
                    body="```suggestion\nvalue = 2\n```",
                    path="file.py",
                    line=0,
                ),
            ],
        )
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 0

    def test_detects_suggestions_from_comment_body(self) -> None:
        """Only comments with ```suggestion code blocks are returned."""
        thread = _make_thread(
            "T1",
            comments=[
                _make_comment(100, comment_id="C1", body="looks good"),
                _make_comment(101, comment_id="C2", body="Please update:\n```suggestion\nvalue = 1\n```"),
                _make_comment(102, comment_id="C3", body="  ```suggestion\nvalue = 2\n```"),
                _make_comment(103, comment_id="C4", body="```suggestion\r\nvalue = 3\r\n```\r\n"),
                _make_comment(104, comment_id="C5", body="```suggestion:-1+1\nvalue = 4\n```"),
                _make_comment(105, comment_id="C6", body="```suggestion:abc\nvalue = 5\n```"),
            ],
        )
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 4
        assert suggestions[0].suggestion_id == "C2"
        assert suggestions[1].suggestion_id == "C3"
        assert suggestions[2].suggestion_id == "C4"
        assert suggestions[3].suggestion_id == "C5"
        assert suggestions[0].comment_database_id == 101

    def test_filters_outdated_thread_suggestions(self) -> None:
        """Suggestions from outdated threads are excluded."""
        thread = _make_thread(
            "T1",
            is_outdated=True,
            comments=[
                _make_comment(100, comment_id="C1", body="```suggestion\nnew line\n```"),
            ],
        )
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert suggestions == []

    def test_skips_resolved_threads(self) -> None:
        """Resolved threads are skipped entirely."""
        thread = _make_thread(
            "T1",
            is_resolved=True,
            comments=[
                _make_comment(100, comment_id="C1", body="```suggestion\nnew line\n```"),
            ],
        )
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert suggestions == []

    def test_pagination(self) -> None:
        """Handles multiple pages of threads."""
        thread1 = _make_thread(
            "T1",
            comments=[_make_comment(100, comment_id="C1", body="```suggestion\nline\n```")],
        )
        thread2 = _make_thread(
            "T2",
            comments=[_make_comment(200, comment_id="C2", body="```suggestion\nline2\n```")],
        )
        provider = _make_provider(
            [
                _build_graphql_response([thread1], has_next_page=True, end_cursor="cursor1"),
                _build_graphql_response([thread2]),
            ]
        )
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 2
        assert suggestions[0].suggestion_id == "C1"
        assert suggestions[1].suggestion_id == "C2"

    def test_paginates_comments_within_thread(self) -> None:
        """Handles comments pagination for a single thread."""
        thread = _make_thread(
            "T1",
            comments=[_make_comment(100, comment_id="C1", body="first comment")],
            comments_has_next_page=True,
            comments_end_cursor="comments-cursor-1",
        )
        paged_comment_response = _build_thread_comments_response(
            [_make_comment(101, comment_id="C2", body="```suggestion\nnew\n```")],
            has_next_page=False,
            end_cursor=None,
        )
        provider = _make_provider([_build_graphql_response([thread]), paged_comment_response])

        suggestions, _ = fetch_applicable_suggestions(provider, 1)

        assert len(suggestions) == 1
        assert suggestions[0].suggestion_id == "C2"
        second_call = provider.graphql.call_args_list[1]
        assert second_call.kwargs["variables"]["threadId"] == "T1"
        assert second_call.kwargs["variables"]["commentsCursor"] == "comments-cursor-1"
        assert "path" in second_call.kwargs["query"]

    def test_thread_comment_schema_error_logs_warning_and_raises_runtime_error(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Schema mismatch while paginating thread comments is fail-closed."""
        thread = _make_thread(
            "T1",
            comments=[_make_comment(100, comment_id="C1", body="first comment")],
            comments_has_next_page=True,
            comments_end_cursor="comments-cursor-1",
        )
        provider = _make_provider(
            [
                _build_graphql_response([thread]),
                {
                    "errors": [{"message": "Cannot query field 'comments' on type 'PullRequestReviewThread'"}],
                },
            ]
        )
        with caplog.at_level(logging.WARNING):
            with pytest.raises(RuntimeError, match="GraphQL query failed"):
                fetch_applicable_suggestions(provider, 1)
        assert "Thread comments GraphQL schema mismatch" in caplog.text

    def test_thread_comment_rate_limit_error_raises_retryable_error(self) -> None:
        """Transient errors from paged thread comments are retryable."""
        thread = _make_thread(
            "T1",
            comments=[_make_comment(100, comment_id="C1", body="first comment")],
            comments_has_next_page=True,
            comments_end_cursor="comments-cursor-1",
        )
        provider = _make_provider(
            [
                _build_graphql_response([thread]),
                {
                    "errors": [{"message": "You have exceeded a secondary rate limit. Please wait a few minutes."}],
                },
            ]
        )
        with pytest.raises(RetryableError, match="Transient GraphQL query error"):
            fetch_applicable_suggestions(provider, 1)

    def test_thread_comment_non_schema_error_raises_runtime_error(self) -> None:
        """Non-transient, non-schema errors from paged comments fail closed."""
        thread = _make_thread(
            "T1",
            comments=[_make_comment(100, comment_id="C1", body="first comment")],
            comments_has_next_page=True,
            comments_end_cursor="comments-cursor-1",
        )
        provider = _make_provider(
            [
                _build_graphql_response([thread]),
                {
                    "errors": [{"message": "Could not resolve node ID"}],
                },
            ]
        )
        with pytest.raises(RuntimeError, match="GraphQL query failed"):
            fetch_applicable_suggestions(provider, 1)

    def test_thread_comment_node_without_comments_dict_is_treated_as_empty(self) -> None:
        """Missing thread comments payload in paged fetch yields no extra comments."""
        thread = _make_thread(
            "T1",
            comments=[_make_comment(100, comment_id="C1", body="first comment")],
            comments_has_next_page=True,
            comments_end_cursor="comments-cursor-1",
        )
        provider = _make_provider(
            [
                _build_graphql_response([thread]),
                {"data": {"node": {"comments": None}}},
            ]
        )
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert suggestions == []

    def test_thread_comment_pageinfo_none_is_treated_as_empty_dict(self) -> None:
        """Null pageInfo in paged thread comments does not crash pagination logic."""
        thread = _make_thread(
            "T1",
            comments=[_make_comment(100, comment_id="C1", body="first comment")],
            comments_has_next_page=True,
            comments_end_cursor="comments-cursor-1",
        )
        provider = _make_provider(
            [
                _build_graphql_response([thread]),
                {
                    "data": {
                        "node": {
                            "comments": {
                                "pageInfo": None,
                                "nodes": [_make_comment(101, comment_id="C2", body="```suggestion\nnew\n```")],
                            }
                        }
                    }
                },
            ]
        )
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 1
        assert suggestions[0].suggestion_id == "C2"

    def test_initial_thread_comments_pageinfo_none_is_treated_as_empty_dict(self) -> None:
        """Null pageInfo on initial thread comments does not crash pagination logic."""
        response = _build_graphql_response(
            [
                {
                    "id": "T1",
                    "isResolved": False,
                    "isOutdated": False,
                    "comments": {
                        "pageInfo": None,
                        "nodes": [_make_comment(101, comment_id="C2", body="```suggestion\nnew\n```")],
                    },
                }
            ]
        )
        provider = _make_provider([response])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 1
        assert suggestions[0].suggestion_id == "C2"
        assert provider.graphql.call_count == 1

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

    def test_schema_error_logs_warning_and_raises_runtime_error(self, caplog: pytest.LogCaptureFixture) -> None:
        """Schema mismatch GraphQL errors are fail-closed with warning logs."""
        provider = _make_provider(
            [
                {
                    "errors": [{"message": "Cannot query field 'suggestedChanges' on type 'PullRequestReviewComment'"}],
                }
            ]
        )
        with caplog.at_level(logging.WARNING):
            with pytest.raises(RuntimeError, match="GraphQL query failed"):
                fetch_applicable_suggestions(provider, 42)
        assert "Suggestion fetch GraphQL schema mismatch" in caplog.text

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
            comments=[_make_comment(100, comment_id="C1", body="```suggestion\nSC1\n```")],
        )
        response = _build_graphql_response([None, valid_thread])
        provider = _make_provider([response])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 1
        assert suggestions[0].suggestion_id == "C1"

    def test_null_comment_node_is_skipped(self) -> None:
        """Null entries in comments.nodes are skipped without error."""
        valid_comment = _make_comment(200, comment_id="C2", body="```suggestion\nSC2\n```")
        thread = _make_thread("T1", comments=[None, valid_comment])
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 1
        assert suggestions[0].suggestion_id == "C2"

    def test_comment_without_id_is_skipped(self) -> None:
        """Comments missing an id field are skipped without error."""
        comment = {
            "databaseId": 300,
            "body": "```suggestion\nSC3\n```",
            "path": "file.py",
            "line": 5,
            "startLine": None,
        }
        thread = _make_thread(
            "T1",
            comments=[comment, _make_comment(301, comment_id="C3", body="```suggestion\nok\n```")],
        )
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 1
        assert suggestions[0].suggestion_id == "C3"

    def test_null_review_threads_value_is_handled(self) -> None:
        """Explicit null for reviewThreads in response yields empty suggestions."""
        response = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "id": "PR_NODE_X",
                        "headRefName": "branch",
                        "headRefOid": "abc123",
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
            "id": "C5",
            "databaseId": "not-an-int",
            "body": "```suggestion\nSC5\n```",
            "path": "file.py",
            "line": 10,
            "startLine": None,
        }
        thread = _make_thread("T1", comments=[comment])
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 1
        assert suggestions[0].comment_database_id == 0

    def test_none_database_id_defaults_to_zero(self) -> None:
        """Explicit null databaseId is coerced to 0 rather than leaking."""
        comment = {
            "id": "C6",
            "databaseId": None,
            "body": "```suggestion\nSC6\n```",
            "path": "file.py",
            "line": 10,
            "startLine": None,
        }
        thread = _make_thread("T1", comments=[comment])
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 1
        assert suggestions[0].comment_database_id == 0

    def test_has_next_page_with_null_cursor_stops_pagination(self) -> None:
        """hasNextPage=True with null endCursor stops pagination rather than looping."""
        thread = _make_thread(
            "T1",
            comments=[_make_comment(100, comment_id="C1", body="```suggestion\nSC1\n```")],
        )
        response = _build_graphql_response([thread], has_next_page=True, end_cursor=None)
        provider = _make_provider([response])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        # Should not loop: only the first page is consumed
        assert provider.graphql.call_count == 1
        assert len(suggestions) == 1
        assert suggestions[0].suggestion_id == "C1"

    def test_malformed_suggestion_block_is_skipped(self) -> None:
        """Suggestion block without closing backticks is skipped."""
        # Block pattern matches the opening line but content pattern requires closing ```
        thread = _make_thread(
            "T1",
            comments=[
                _make_comment(
                    100,
                    comment_id="C1",
                    body="```suggestion\nsome content without closing fence",
                    path="src/file.py",
                    line=5,
                    start_line=5,
                ),
            ],
        )
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert suggestions == []

    def test_empty_suggestion_block_is_valid_delete(self) -> None:
        """Empty suggestion block is retained as an empty replacement (delete)."""
        thread = _make_thread(
            "T1",
            comments=[
                _make_comment(
                    100,
                    comment_id="C1",
                    body="```suggestion\n```",
                    path="src/file.py",
                    line=5,
                    start_line=5,
                ),
            ],
        )
        provider = _make_provider([_build_graphql_response([thread])])
        suggestions, _ = fetch_applicable_suggestions(provider, 1)
        assert len(suggestions) == 1
        assert suggestions[0].suggestion_id == "C1"
        assert suggestions[0].replacement == ""
