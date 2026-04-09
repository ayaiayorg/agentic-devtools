"""Tests for get_agdt_threads convenience wrapper."""

from agentic_devtools.cli.azure_devops.review_helpers import get_agdt_threads


def _make_thread(thread_id: int, content: str) -> dict:
    """Build a minimal thread dict for testing."""
    return {"id": thread_id, "comments": [{"content": content}]}


class TestGetAgdtThreads:
    """Tests for get_agdt_threads."""

    def test_returns_only_marked_threads(self):
        """Filters to only threads with agdt-review markers."""
        threads = [
            _make_thread(1, "<!-- agdt-review:v1 type:file-summary -->\nContent"),
            _make_thread(2, "Human comment"),
        ]
        result = get_agdt_threads(threads)
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_empty_list(self):
        """Returns empty list for empty input."""
        assert get_agdt_threads([]) == []

    def test_no_marked_threads(self):
        """Returns empty when no threads have markers."""
        threads = [_make_thread(1, "no marker")]
        assert get_agdt_threads(threads) == []
