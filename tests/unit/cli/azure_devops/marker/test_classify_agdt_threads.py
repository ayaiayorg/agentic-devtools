"""Tests for classify_agdt_threads function."""

from agentic_devtools.cli.azure_devops.marker import classify_agdt_threads


def _make_thread(thread_id: int, content: str) -> dict:
    """Build a minimal thread dict for testing."""
    return {"id": thread_id, "comments": [{"content": content}]}


class TestClassifyAgdtThreads:
    """Tests for classify_agdt_threads."""

    def test_empty_list(self):
        """Returns empty dict for empty input."""
        assert classify_agdt_threads([]) == {}

    def test_groups_by_type(self):
        """Groups threads by their marker type."""
        threads = [
            _make_thread(1, "<!-- agdt-review:v1 type:file-summary -->"),
            _make_thread(2, "<!-- agdt-review:v1 type:suggestion -->"),
            _make_thread(3, "<!-- agdt-review:v1 type:file-summary -->"),
        ]
        result = classify_agdt_threads(threads)
        assert len(result["file-summary"]) == 2
        assert len(result["suggestion"]) == 1

    def test_excludes_unmarked_threads(self):
        """Threads without markers are excluded."""
        threads = [
            _make_thread(1, "no marker"),
            _make_thread(2, "<!-- agdt-review:v1 type:overall-summary -->"),
        ]
        result = classify_agdt_threads(threads)
        assert "overall-summary" in result
        assert len(result) == 1

    def test_handles_none_in_list(self):
        """Skips None entries."""
        threads = [
            None,
            _make_thread(1, "<!-- agdt-review:v1 type:activity-log -->"),
        ]
        result = classify_agdt_threads(threads)
        assert len(result["activity-log"]) == 1

    def test_no_marked_threads(self):
        """Returns empty dict when no threads have markers."""
        threads = [_make_thread(1, "human comment")]
        assert classify_agdt_threads(threads) == {}

    def test_skips_marker_without_type(self):
        """Skips threads whose marker has no type key."""
        threads = [
            {"id": 1, "comments": [{"content": "<!-- agdt-review:v1 file:/a.ts -->"}]},
            _make_thread(2, "<!-- agdt-review:v1 type:suggestion -->"),
        ]
        result = classify_agdt_threads(threads)
        assert "suggestion" in result
        assert len(result) == 1

    def test_skips_marker_with_empty_type(self):
        """Skips threads whose marker has an empty type value."""
        threads = [
            _make_thread(1, "<!-- agdt-review:v1 type: file:/a.ts -->"),
            _make_thread(2, "<!-- agdt-review:v1 type:suggestion -->"),
        ]
        result = classify_agdt_threads(threads)
        assert "suggestion" in result
        assert len(result) == 1
