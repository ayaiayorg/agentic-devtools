"""Tests for _map_comments_to_threads pure function."""

from agentic_devtools.cli.github.resolve_review_threads import (
    _map_comments_to_threads,
)


class TestMapCommentsToThreads:
    """Tests for _map_comments_to_threads."""

    def test_matching_threads_found(self):
        """Return threads whose first comment databaseId is in target set."""
        threads = [
            {"id": "PRT_a", "isResolved": False, "comments": {"nodes": [{"databaseId": 1}]}},
            {"id": "PRT_b", "isResolved": True, "comments": {"nodes": [{"databaseId": 2}]}},
            {"id": "PRT_c", "isResolved": False, "comments": {"nodes": [{"databaseId": 3}]}},
        ]
        result = _map_comments_to_threads(threads, {1, 3})
        assert len(result) == 2
        assert result[0] == {"threadId": "PRT_a", "commentId": 1, "isResolved": False}
        assert result[1] == {"threadId": "PRT_c", "commentId": 3, "isResolved": False}

    def test_no_matches(self):
        """Return empty list when no comments match."""
        threads = [
            {"id": "PRT_a", "isResolved": False, "comments": {"nodes": [{"databaseId": 1}]}},
        ]
        result = _map_comments_to_threads(threads, {999})
        assert result == []

    def test_already_resolved_threads_included(self):
        """Already-resolved threads still appear with isResolved=True."""
        threads = [
            {"id": "PRT_a", "isResolved": True, "comments": {"nodes": [{"databaseId": 10}]}},
        ]
        result = _map_comments_to_threads(threads, {10})
        assert len(result) == 1
        assert result[0]["isResolved"] is True

    def test_empty_comments_skipped(self):
        """Threads with empty comments nodes are safely skipped."""
        threads = [
            {"id": "PRT_a", "isResolved": False, "comments": {"nodes": []}},
            {"id": "PRT_b", "isResolved": False, "comments": {"nodes": [{"databaseId": 5}]}},
        ]
        result = _map_comments_to_threads(threads, {5})
        assert len(result) == 1
        assert result[0]["threadId"] == "PRT_b"

    def test_missing_comments_key_skipped(self):
        """Threads missing the comments key are safely skipped."""
        threads = [
            {"id": "PRT_a", "isResolved": False},
            {"id": "PRT_b", "isResolved": False, "comments": {"nodes": [{"databaseId": 7}]}},
        ]
        result = _map_comments_to_threads(threads, {7})
        assert len(result) == 1

    def test_mixed_resolved_and_unresolved(self):
        """Mixed set of resolved/unresolved threads returned correctly."""
        threads = [
            {"id": "PRT_a", "isResolved": True, "comments": {"nodes": [{"databaseId": 1}]}},
            {"id": "PRT_b", "isResolved": False, "comments": {"nodes": [{"databaseId": 2}]}},
        ]
        result = _map_comments_to_threads(threads, {1, 2})
        assert len(result) == 2
        statuses = {r["threadId"]: r["isResolved"] for r in result}
        assert statuses["PRT_a"] is True
        assert statuses["PRT_b"] is False

    def test_match_on_reply_comment(self):
        """Match a reply comment ID (not the first comment in the thread)."""
        threads = [
            {
                "id": "PRT_a",
                "isResolved": False,
                "comments": {"nodes": [{"databaseId": 1}, {"databaseId": 2}, {"databaseId": 3}]},
            },
        ]
        result = _map_comments_to_threads(threads, {3})
        assert len(result) == 1
        assert result[0]["commentId"] == 3
        assert result[0]["threadId"] == "PRT_a"

    def test_first_matching_comment_wins(self):
        """When multiple comments in a thread match, the first match is used."""
        threads = [
            {
                "id": "PRT_a",
                "isResolved": False,
                "comments": {"nodes": [{"databaseId": 10}, {"databaseId": 20}]},
            },
        ]
        result = _map_comments_to_threads(threads, {10, 20})
        assert len(result) == 1
        assert result[0]["commentId"] == 10
