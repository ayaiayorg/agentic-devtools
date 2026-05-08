"""Tests for strip_marker_line function."""

from agentic_devtools.cli.azure_devops.marker import strip_marker_line


class TestStripMarkerLine:
    """Tests for strip_marker_line."""

    def test_strips_marker_from_first_line(self):
        """Should remove the marker line and return remaining content."""
        content = "<!-- agdt-review:v1 type:file-summary -->\n## File Review Summary"
        result = strip_marker_line(content)
        assert result == "## File Review Summary"

    def test_returns_unchanged_when_no_marker(self):
        """Should return content unchanged when no marker is present."""
        content = "## File Review Summary\nSome content"
        result = strip_marker_line(content)
        assert result == content

    def test_returns_empty_for_marker_only(self):
        """Should return empty string when content is only a marker."""
        content = "<!-- agdt-review:v1 type:file-summary -->"
        result = strip_marker_line(content)
        assert result == ""

    def test_returns_empty_string_unchanged(self):
        """Should return empty string for empty input."""
        assert strip_marker_line("") == ""

    def test_preserves_multiline_content_after_marker(self):
        """Should preserve all content after the marker line."""
        content = "<!-- agdt-review:v1 type:overall-summary -->\nLine 1\nLine 2\nLine 3"
        result = strip_marker_line(content)
        assert result == "Line 1\nLine 2\nLine 3"

    def test_no_false_positive_on_non_marker_comment(self):
        """Should not strip non-AGDT HTML comments."""
        content = "<!-- some other comment -->\nContent"
        result = strip_marker_line(content)
        assert result == content

    def test_only_strips_first_line(self):
        """Should only strip the first line marker, not embedded markers."""
        content = "<!-- agdt-review:v1 type:file-summary -->\nContent\n<!-- agdt-review:v1 type:suggestion -->"
        result = strip_marker_line(content)
        assert result == "Content\n<!-- agdt-review:v1 type:suggestion -->"
