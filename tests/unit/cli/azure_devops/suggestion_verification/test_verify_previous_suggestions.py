"""Tests for verify_previous_suggestions pure function."""

from agentic_devtools.cli.azure_devops.review_state import SuggestionEntry
from agentic_devtools.cli.azure_devops.suggestion_verification import (
    CATEGORY_NEEDS_REVIEW,
    CATEGORY_UNADDRESSED,
    verify_previous_suggestions,
)


def _make_suggestion(thread_id: int = 100, **kwargs) -> SuggestionEntry:
    defaults = {
        "threadId": thread_id,
        "commentId": 200,
        "line": 10,
        "endLine": 20,
        "severity": "high",
        "outOfScope": False,
        "linkText": "lines 10 - 20",
        "content": "Missing null check",
    }
    defaults.update(kwargs)
    return SuggestionEntry(**defaults)


def _make_thread(thread_id: int, num_comments: int = 1, status: str = "active"):
    """Build a minimal Azure DevOps thread response dict."""
    comments = [{"id": i + 1, "content": f"comment {i + 1}"} for i in range(num_comments)]
    return {"id": thread_id, "comments": comments, "status": status}


class TestVerifyPreviousSuggestions:
    """Tests for the verify_previous_suggestions function."""

    def test_no_reply_no_file_change_is_unaddressed(self):
        """No reply + no file change → unaddressed."""
        sug = _make_suggestion(thread_id=1)
        threads = {1: _make_thread(1, num_comments=1)}
        results = verify_previous_suggestions([sug], "/src/app.py", False, threads)
        assert len(results) == 1
        assert results[0].category == CATEGORY_UNADDRESSED
        assert results[0].has_reply is False
        assert results[0].file_changed is False

    def test_reply_exists_no_file_change_is_needs_review(self):
        """Reply exists + no file change → needs_review."""
        sug = _make_suggestion(thread_id=2)
        threads = {2: _make_thread(2, num_comments=2)}
        results = verify_previous_suggestions([sug], "/src/app.py", False, threads)
        assert len(results) == 1
        assert results[0].category == CATEGORY_NEEDS_REVIEW
        assert results[0].has_reply is True
        assert results[0].file_changed is False

    def test_no_reply_file_changed_is_needs_review(self):
        """No reply + file changed → needs_review."""
        sug = _make_suggestion(thread_id=3)
        threads = {3: _make_thread(3, num_comments=1)}
        results = verify_previous_suggestions([sug], "/src/app.py", True, threads)
        assert len(results) == 1
        assert results[0].category == CATEGORY_NEEDS_REVIEW
        assert results[0].has_reply is False
        assert results[0].file_changed is True

    def test_reply_exists_file_changed_is_needs_review(self):
        """Reply exists + file changed → needs_review."""
        sug = _make_suggestion(thread_id=4)
        threads = {4: _make_thread(4, num_comments=3)}
        results = verify_previous_suggestions([sug], "/src/app.py", True, threads)
        assert len(results) == 1
        assert results[0].category == CATEGORY_NEEDS_REVIEW
        assert results[0].has_reply is True
        assert results[0].file_changed is True

    def test_thread_not_found_is_needs_review(self):
        """Thread not found in data → needs_review (unknown state)."""
        sug = _make_suggestion(thread_id=999)
        threads = {}
        results = verify_previous_suggestions([sug], "/src/app.py", False, threads)
        assert len(results) == 1
        assert results[0].category == CATEGORY_NEEDS_REVIEW
        assert results[0].thread_status == "unknown"

    def test_resolved_thread_no_reply_no_changes_is_unaddressed(self):
        """Resolved thread + no reply + no changes → unaddressed (suspicious auto-resolve)."""
        sug = _make_suggestion(thread_id=5)
        threads = {5: _make_thread(5, num_comments=1, status="closed")}
        results = verify_previous_suggestions([sug], "/src/app.py", False, threads)
        assert len(results) == 1
        assert results[0].category == CATEGORY_UNADDRESSED
        assert results[0].thread_status == "closed"

    def test_empty_suggestions_returns_empty(self):
        """Empty suggestions list → empty result."""
        results = verify_previous_suggestions([], "/src/app.py", False, {})
        assert results == []

    def test_multiple_suggestions_mixed(self):
        """Multiple suggestions with mixed categories."""
        sug1 = _make_suggestion(thread_id=10)
        sug2 = _make_suggestion(thread_id=11)
        threads = {
            10: _make_thread(10, num_comments=1),  # no reply
            11: _make_thread(11, num_comments=2),  # has reply
        }
        results = verify_previous_suggestions([sug1, sug2], "/src/app.py", False, threads)
        assert len(results) == 2
        assert results[0].category == CATEGORY_UNADDRESSED
        assert results[1].category == CATEGORY_NEEDS_REVIEW

    def test_file_path_preserved(self):
        """File path is stored in result."""
        sug = _make_suggestion(thread_id=1)
        threads = {1: _make_thread(1)}
        results = verify_previous_suggestions([sug], "/my/path.ts", False, threads)
        assert results[0].file_path == "/my/path.ts"

    def test_suggestion_object_preserved(self):
        """Original suggestion object is preserved in result."""
        sug = _make_suggestion(thread_id=1, content="Fix this bug")
        threads = {1: _make_thread(1)}
        results = verify_previous_suggestions([sug], "/src/app.py", False, threads)
        assert results[0].suggestion is sug
        assert results[0].suggestion.content == "Fix this bug"
