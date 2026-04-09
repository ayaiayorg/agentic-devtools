"""Tests for build_marker function."""

import pytest

from agentic_devtools.cli.azure_devops.marker import build_marker, parse_marker


class TestBuildMarker:
    """Tests for build_marker."""

    def test_basic_file_summary(self):
        """Builds a file-summary marker with file and pr."""
        result = build_marker("file-summary", file="/src/app.ts", pr=123)
        assert result == "<!-- agdt-review:v1 type:file-summary file:/src/app.ts pr:123 -->"

    def test_overall_summary(self):
        """Builds an overall-summary marker with pr only."""
        result = build_marker("overall-summary", pr=456)
        assert result == "<!-- agdt-review:v1 type:overall-summary pr:456 -->"

    def test_activity_log(self):
        """Builds an activity-log marker."""
        result = build_marker("activity-log", pr=789)
        assert result == "<!-- agdt-review:v1 type:activity-log pr:789 -->"

    def test_suggestion_with_all_params(self):
        """Builds a suggestion marker with all optional fields."""
        result = build_marker("suggestion", file="/src/utils.ts", pr=100, line=42, severity="high")
        assert result == "<!-- agdt-review:v1 type:suggestion file:/src/utils.ts pr:100 line:42 severity:high -->"

    def test_type_only(self):
        """Builds a marker with only the required type."""
        result = build_marker("activity-log-entry")
        assert result == "<!-- agdt-review:v1 type:activity-log-entry -->"

    def test_invalid_type_raises(self):
        """Raises ValueError for unrecognised marker type."""
        with pytest.raises(ValueError, match="Unknown marker type"):
            build_marker("invalid-type")

    def test_all_valid_types(self):
        """All recognised types produce valid markers."""
        valid_types = [
            "file-summary",
            "overall-summary",
            "activity-log",
            "suggestion",
            "activity-log-entry",
            "legacy-approval",
            "legacy-summary",
            "legacy-suggestion",
        ]
        for t in valid_types:
            result = build_marker(t)
            assert result.startswith("<!-- agdt-review:v1 type:")
            assert result.endswith(" -->")

    def test_file_none_excluded(self):
        """When file is None, the file key is omitted."""
        result = build_marker("overall-summary", pr=1)
        assert "file:" not in result

    def test_line_none_excluded(self):
        """When line is None, the line key is omitted."""
        result = build_marker("file-summary", file="/a.ts")
        assert "line:" not in result

    def test_severity_none_excluded(self):
        """When severity is None, the severity key is omitted."""
        result = build_marker("file-summary")
        assert "severity:" not in result

    def test_file_with_spaces_is_encoded(self):
        """File paths containing spaces are percent-encoded."""
        result = build_marker("file-summary", file="/src/my file.ts", pr=1)
        assert "%20" in result
        assert "my file" not in result  # raw space in the value must be encoded

    def test_file_with_html_comment_close_is_encoded(self):
        """The --> sequence in a file path is safely encoded."""
        result = build_marker("file-summary", file="/src/a-->b.ts", pr=1)
        assert result.endswith(" -->")
        assert result.count("-->") == 1  # only the final HTML comment close is allowed
        assert "%3E" in result  # '>' is encoded

    def test_round_trip_file_with_spaces(self):
        """build_marker + parse_marker round-trips file paths with spaces."""
        original = "/src/my file/path here.ts"
        marker = build_marker("file-summary", file=original, pr=42)
        parsed = parse_marker(marker)
        assert parsed is not None
        assert parsed["file"] == original
