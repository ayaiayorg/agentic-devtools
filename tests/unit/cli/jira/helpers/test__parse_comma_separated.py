"""
Tests for Jira helper utilities.
"""

from agdt_ai_helpers.cli import jira


class TestParseCommaSeparated:
    """Tests for _parse_comma_separated helper."""

    def test_parse_none_returns_none(self):
        """Test None input returns None."""
        assert jira._parse_comma_separated(None) is None

    def test_parse_list_returns_stripped_list(self):
        """Test list input returns stripped items."""
        items = ["  a  ", "b", "  c"]
        assert jira._parse_comma_separated(items) == ["a", "b", "c"]

    def test_parse_list_filters_empty(self):
        """Test empty items are filtered from list."""
        items = ["a", "", "  ", "b"]
        assert jira._parse_comma_separated(items) == ["a", "b"]

    def test_parse_comma_separated_string(self):
        """Test comma-separated string is split."""
        result = jira._parse_comma_separated("a,b,c")
        assert result == ["a", "b", "c"]

    def test_parse_string_strips_whitespace(self):
        """Test whitespace is stripped from each item."""
        result = jira._parse_comma_separated("  a  ,  b  ,  c  ")
        assert result == ["a", "b", "c"]

    def test_parse_string_skips_empty_items(self):
        """Test empty items are skipped."""
        result = jira._parse_comma_separated("a,,  ,b")
        assert result == ["a", "b"]

    def test_parse_integer_returns_none(self):
        """Test non-string non-list input returns None."""
        assert jira._parse_comma_separated(123) is None

    def test_parse_empty_string_returns_empty_list(self):
        """Test empty string returns empty list."""
        assert jira._parse_comma_separated("") == []

    def test_parse_empty_list_returns_empty_list(self):
        """Test empty list returns empty list."""
        assert jira._parse_comma_separated([]) == []
