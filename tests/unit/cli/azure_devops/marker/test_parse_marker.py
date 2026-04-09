"""Tests for parse_marker function."""

from agentic_devtools.cli.azure_devops.marker import parse_marker


class TestParseMarker:
    """Tests for parse_marker."""

    def test_valid_marker(self):
        """Parses a valid marker with multiple keys."""
        content = "<!-- agdt-review:v1 type:file-summary file:/src/app.ts pr:123 -->\nsome content"
        result = parse_marker(content)
        assert result == {"_version": "1", "type": "file-summary", "file": "/src/app.ts", "pr": "123"}

    def test_marker_with_type_only(self):
        """Parses a marker with only a type."""
        content = "<!-- agdt-review:v1 type:overall-summary -->"
        result = parse_marker(content)
        assert result == {"_version": "1", "type": "overall-summary"}

    def test_no_marker(self):
        """Returns None when no marker is present."""
        result = parse_marker("just regular content")
        assert result is None

    def test_empty_string(self):
        """Returns None for empty string."""
        result = parse_marker("")
        assert result is None

    def test_malformed_marker(self):
        """Returns None for truncated/malformed marker."""
        result = parse_marker("<!-- agdt-review:v1")
        assert result is None

    def test_unknown_keys_included(self):
        """Unknown keys are included in the result dict."""
        content = "<!-- agdt-review:v1 type:file-summary custom:value -->"
        result = parse_marker(content)
        assert result is not None
        assert result["custom"] == "value"

    def test_multiple_markers_returns_first(self):
        """When multiple markers exist, returns the first one."""
        content = "<!-- agdt-review:v1 type:file-summary -->\n<!-- agdt-review:v1 type:suggestion -->"
        result = parse_marker(content)
        assert result is not None
        assert result["type"] == "file-summary"

    def test_marker_embedded_in_content(self):
        """Parses marker when embedded mid-content."""
        content = "prefix\n<!-- agdt-review:v1 type:suggestion line:42 severity:high -->\nsuffix"
        result = parse_marker(content)
        assert result == {"_version": "1", "type": "suggestion", "line": "42", "severity": "high"}

    def test_marker_with_suggestion_fields(self):
        """Parses suggestion marker with file, pr, line, severity."""
        content = "<!-- agdt-review:v1 type:suggestion file:/src/u.ts pr:99 line:10 severity:low -->"
        result = parse_marker(content)
        assert result == {
            "_version": "1",
            "type": "suggestion",
            "file": "/src/u.ts",
            "pr": "99",
            "line": "10",
            "severity": "low",
        }

    def test_empty_payload_returns_none(self):
        """Returns None when marker payload is empty."""
        content = "<!-- agdt-review:v1  -->"
        result = parse_marker(content)
        assert result is None

    def test_url_encoded_file_with_spaces(self):
        """Decodes a URL-encoded file path containing spaces."""
        content = "<!-- agdt-review:v1 type:file-summary file:/src/my%20file.ts pr:1 -->"
        result = parse_marker(content)
        assert result is not None
        assert result["file"] == "/src/my file.ts"

    def test_version_included_in_result(self):
        """The _version key is present in parsed output."""
        content = "<!-- agdt-review:v1 type:file-summary -->"
        result = parse_marker(content)
        assert result is not None
        assert result["_version"] == "1"

    def test_payload_cannot_overwrite_version(self):
        """A _version token in the payload must not overwrite the header version."""
        content = "<!-- agdt-review:v1 _version:99 type:file-summary -->"
        result = parse_marker(content)
        assert result is not None
        assert result["_version"] == "1"
