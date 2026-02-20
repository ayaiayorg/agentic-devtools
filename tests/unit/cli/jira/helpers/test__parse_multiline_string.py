"""
Tests for Jira helper utilities.
"""

from agdt_ai_helpers.cli import jira


class TestParseMultilineString:
    """Tests for _parse_multiline_string helper."""

    def test_parse_none_returns_none(self):
        """Test None input returns None."""
        assert jira._parse_multiline_string(None) is None

    def test_parse_list_returns_stripped_list(self):
        """Test list input returns stripped items."""
        items = ["  a  ", "b", "  c"]
        assert jira._parse_multiline_string(items) == ["a", "b", "c"]

    def test_parse_list_filters_empty(self):
        """Test empty items are filtered from list."""
        items = ["a", "", "  ", "b"]
        assert jira._parse_multiline_string(items) == ["a", "b"]

    def test_parse_newline_separated_string(self):
        """Test newline-separated string is split."""
        result = jira._parse_multiline_string("line1\nline2\nline3")
        assert result == ["line1", "line2", "line3"]

    def test_parse_string_strips_whitespace(self):
        """Test whitespace is stripped from each line."""
        result = jira._parse_multiline_string("  line1  \n  line2  ")
        assert result == ["line1", "line2"]

    def test_parse_string_skips_empty_lines(self):
        """Test empty lines are skipped."""
        result = jira._parse_multiline_string("line1\n\n  \nline2")
        assert result == ["line1", "line2"]

    def test_parse_integer_returns_none(self):
        """Test non-string non-list input returns None."""
        assert jira._parse_multiline_string(123) is None

    def test_parse_empty_string_returns_empty_list(self):
        """Test empty string returns empty list."""
        assert jira._parse_multiline_string("") == []

    def test_parse_empty_list_returns_empty_list(self):
        """Test empty list returns empty list."""
        assert jira._parse_multiline_string([]) == []

