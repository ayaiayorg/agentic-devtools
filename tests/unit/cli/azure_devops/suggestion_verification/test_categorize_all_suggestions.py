"""Tests for categorize_all_suggestions function."""

from agentic_devtools.cli.azure_devops.review_state import SuggestionEntry
from agentic_devtools.cli.azure_devops.suggestion_verification import (
    CATEGORY_NEEDS_REVIEW,
    CATEGORY_UNADDRESSED,
    categorize_all_suggestions,
)


def _make_suggestion(thread_id: int = 100) -> SuggestionEntry:
    return SuggestionEntry(
        threadId=thread_id,
        commentId=200,
        line=10,
        endLine=20,
        severity="high",
        outOfScope=False,
        linkText="lines 10 - 20",
        content="Missing null check",
    )


def _make_thread(thread_id: int, num_comments: int = 1, status: str = "active"):
    comments = [{"id": i + 1, "content": f"comment {i + 1}"} for i in range(num_comments)]
    return {"id": thread_id, "comments": comments, "status": status}


class TestCategorizeAllSuggestions:
    """Tests for categorize_all_suggestions."""

    def test_empty_input(self):
        """No files with previous suggestions → empty result."""
        results = categorize_all_suggestions({}, frozenset(), {})
        assert results == []

    def test_single_file_unaddressed(self):
        """Single file, no changes, no reply → unaddressed."""
        sug = _make_suggestion(thread_id=1)
        threads = {1: _make_thread(1, num_comments=1)}
        results = categorize_all_suggestions({"/src/a.py": [sug]}, frozenset(), threads)
        assert len(results) == 1
        assert results[0].category == CATEGORY_UNADDRESSED

    def test_single_file_needs_review_because_changed(self):
        """Single file changed → needs_review."""
        sug = _make_suggestion(thread_id=1)
        threads = {1: _make_thread(1, num_comments=1)}
        results = categorize_all_suggestions({"/src/a.py": [sug]}, frozenset(["/src/a.py"]), threads)
        assert len(results) == 1
        assert results[0].category == CATEGORY_NEEDS_REVIEW

    def test_multiple_files(self):
        """Multiple files across different categories."""
        sug_a = _make_suggestion(thread_id=1)
        sug_b = _make_suggestion(thread_id=2)
        threads = {
            1: _make_thread(1, num_comments=1),  # no reply
            2: _make_thread(2, num_comments=2),  # has reply
        }
        results = categorize_all_suggestions(
            {"/src/a.py": [sug_a], "/src/b.py": [sug_b]},
            frozenset(),  # no file changes
            threads,
        )
        assert len(results) == 2
        cats = {r.file_path: r.category for r in results}
        assert cats["/src/a.py"] == CATEGORY_UNADDRESSED
        assert cats["/src/b.py"] == CATEGORY_NEEDS_REVIEW

    def test_file_changed_overrides_no_reply(self):
        """File in changed set with no reply → needs_review."""
        sug = _make_suggestion(thread_id=10)
        threads = {10: _make_thread(10, num_comments=1)}
        results = categorize_all_suggestions({"/src/x.ts": [sug]}, frozenset(["/src/x.ts"]), threads)
        assert results[0].category == CATEGORY_NEEDS_REVIEW
        assert results[0].file_changed is True

    def test_deleted_file_in_changed_set_is_needs_review(self):
        """Deleted file in changed set with no reply → needs_review, not unaddressed."""
        sug = _make_suggestion(thread_id=5)
        threads = {5: _make_thread(5, num_comments=1)}
        # Deleted file should be in the changed_files set
        results = categorize_all_suggestions({"/src/removed.ts": [sug]}, frozenset(["/src/removed.ts"]), threads)
        assert len(results) == 1
        assert results[0].category == CATEGORY_NEEDS_REVIEW
        assert results[0].file_changed is True
