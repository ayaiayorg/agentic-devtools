"""Tests for filter_agdt_threads function."""

from agentic_devtools.cli.azure_devops.marker import filter_agdt_threads


def _make_thread(thread_id: int, content: str) -> dict:
    """Build a minimal thread dict for testing."""
    return {"id": thread_id, "comments": [{"content": content}]}


class TestFilterAgdtThreads:
    """Tests for filter_agdt_threads."""

    def test_empty_list(self):
        """Returns empty list for empty input."""
        assert filter_agdt_threads([]) == []

    def test_filters_only_marked_threads(self):
        """Returns only threads whose first comment contains a marker."""
        threads = [
            _make_thread(1, "<!-- agdt-review:v1 type:file-summary -->\nContent"),
            _make_thread(2, "Human review comment"),
            _make_thread(3, "<!-- agdt-review:v1 type:suggestion -->\nSuggestion"),
        ]
        result = filter_agdt_threads(threads)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 3

    def test_no_marked_threads(self):
        """Returns empty list when no threads have markers."""
        threads = [
            _make_thread(1, "Some comment"),
            _make_thread(2, "Another comment"),
        ]
        assert filter_agdt_threads(threads) == []

    def test_handles_none_in_list(self):
        """Skips None entries in the thread list."""
        threads = [
            None,
            _make_thread(1, "<!-- agdt-review:v1 type:file-summary -->"),
        ]
        result = filter_agdt_threads(threads)
        assert len(result) == 1

    def test_handles_thread_without_comments(self):
        """Skips threads with no comments."""
        threads = [
            {"id": 1},
            _make_thread(2, "<!-- agdt-review:v1 type:suggestion -->"),
        ]
        result = filter_agdt_threads(threads)
        assert len(result) == 1
        assert result[0]["id"] == 2

    def test_handles_empty_comments_list(self):
        """Skips threads with empty comments list."""
        threads = [
            {"id": 1, "comments": []},
            _make_thread(2, "<!-- agdt-review:v1 type:file-summary -->"),
        ]
        result = filter_agdt_threads(threads)
        assert len(result) == 1

    def test_handles_non_dict_first_comment(self):
        """Skips threads where first comment is not a dict."""
        threads = [
            {"id": 1, "comments": ["not a dict"]},
            _make_thread(2, "<!-- agdt-review:v1 type:file-summary -->"),
        ]
        result = filter_agdt_threads(threads)
        assert len(result) == 1
        assert result[0]["id"] == 2
