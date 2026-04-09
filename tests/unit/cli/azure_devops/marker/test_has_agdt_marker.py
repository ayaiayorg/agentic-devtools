"""Tests for has_agdt_marker function."""

from agentic_devtools.cli.azure_devops.marker import has_agdt_marker


class TestHasAgdtMarker:
    """Tests for has_agdt_marker."""

    def test_positive_match(self):
        """Returns True when content contains a marker."""
        assert has_agdt_marker("<!-- agdt-review:v1 type:file-summary -->") is True

    def test_no_marker(self):
        """Returns False when content has no marker."""
        assert has_agdt_marker("plain text content") is False

    def test_empty_string(self):
        """Returns False for empty string."""
        assert has_agdt_marker("") is False

    def test_marker_in_larger_content(self):
        """Returns True when marker is embedded in larger content."""
        content = "# Header\n<!-- agdt-review:v1 type:suggestion -->\nMore text"
        assert has_agdt_marker(content) is True

    def test_similar_but_different_comment(self):
        """Returns False for HTML comments that don't match the marker pattern."""
        assert has_agdt_marker("<!-- activity-seq:7 -->") is False

    def test_partial_marker(self):
        """Returns False for incomplete markers."""
        assert has_agdt_marker("<!-- agdt-review:v1") is False

    def test_empty_payload_marker(self):
        """Returns False when marker regex matches but payload is empty."""
        assert has_agdt_marker("<!-- agdt-review:v1  -->") is False

    def test_marker_without_type_key(self):
        """Returns False when marker has keys but no type key."""
        assert has_agdt_marker("<!-- agdt-review:v1 file:/src/app.ts -->") is False

    def test_unrecognized_type_returns_false(self):
        """Returns False when marker type is not in MARKER_TYPES."""
        assert has_agdt_marker("<!-- agdt-review:v1 type:unknown-type -->") is False

    def test_all_known_types_return_true(self):
        """Returns True for every recognised marker type."""
        from agentic_devtools.cli.azure_devops.marker import MARKER_TYPES

        for t in sorted(MARKER_TYPES):
            assert has_agdt_marker(f"<!-- agdt-review:v1 type:{t} -->") is True
