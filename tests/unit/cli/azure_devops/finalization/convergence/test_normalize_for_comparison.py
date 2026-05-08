"""Tests for normalize_for_comparison function."""

from agentic_devtools.cli.azure_devops.finalization.convergence import normalize_for_comparison


class TestNormalizeForComparison:
    """Tests for normalize_for_comparison."""

    def test_strips_marker_line(self):
        """Should strip the leading marker line."""
        content = "<!-- agdt-review:v1 type:file-summary -->\n## File Review Summary"
        result = normalize_for_comparison(content)
        assert result == "## File Review Summary"

    def test_passthrough_when_no_marker(self):
        """Should return content unchanged when no marker present."""
        content = "## File Review Summary\nSome content"
        result = normalize_for_comparison(content)
        assert result == content

    def test_empty_string(self):
        """Should handle empty string."""
        assert normalize_for_comparison("") == ""
