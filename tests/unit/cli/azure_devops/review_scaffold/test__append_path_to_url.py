"""Tests for _append_path_to_url helper function."""

from agentic_devtools.cli.azure_devops.review_scaffold import _append_path_to_url


class TestAppendPathToUrl:
    """Tests for _append_path_to_url helper."""

    def test_appends_single_segment_without_query(self):
        """Appends a single segment when URL has no query string."""
        result = _append_path_to_url("https://api/threads", 42)
        assert result == "https://api/threads/42"

    def test_appends_multiple_segments_without_query(self):
        """Appends multiple segments when URL has no query string."""
        result = _append_path_to_url("https://api/threads", 42, "comments")
        assert result == "https://api/threads/42/comments"

    def test_inserts_segments_before_query_string(self):
        """Inserts segments before ?api-version=7.0."""
        result = _append_path_to_url("https://api/threads?api-version=7.0", 42)
        assert result == "https://api/threads/42?api-version=7.0"

    def test_inserts_multiple_segments_before_query_string(self):
        """Inserts multiple segments before the query string."""
        result = _append_path_to_url("https://api/threads?api-version=7.0", 42, "comments", 1)
        assert result == "https://api/threads/42/comments/1?api-version=7.0"

    def test_preserves_multiple_query_params(self):
        """Preserves all query parameters when multiple are present."""
        result = _append_path_to_url("https://api/threads?api-version=7.0&extra=1", 42)
        assert result == "https://api/threads/42?api-version=7.0&extra=1"

    def test_handles_integer_segments(self):
        """Converts integer segments to strings."""
        result = _append_path_to_url("https://api/threads?api-version=7.0", 10, "comments", 5)
        assert result == "https://api/threads/10/comments/5?api-version=7.0"

    def test_returns_base_url_unchanged_when_no_segments(self):
        """Returns the original URL when no segments are provided."""
        assert _append_path_to_url("https://api/threads") == "https://api/threads"
        assert _append_path_to_url("https://api/threads?api-version=7.0") == "https://api/threads?api-version=7.0"

    def test_no_double_slash_when_base_has_trailing_slash(self):
        """Avoids double slashes when base URL has a trailing slash."""
        result = _append_path_to_url("https://api/threads/", 42)
        assert result == "https://api/threads/42"

    def test_no_double_slash_when_base_has_trailing_slash_with_query(self):
        """Avoids double slashes when base URL has a trailing slash and query string."""
        result = _append_path_to_url("https://api/threads/?api-version=7.0", 42)
        assert result == "https://api/threads/42?api-version=7.0"
