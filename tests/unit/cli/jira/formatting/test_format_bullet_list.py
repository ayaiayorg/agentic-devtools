"""
Tests for Jira formatting utilities.
"""


from agdt_ai_helpers.cli import jira


class TestFormatBulletList:
    """Tests for format_bullet_list function."""

    def test_format_bullet_list_empty(self):
        """Test empty list returns empty string."""
        assert jira.format_bullet_list([]) == ""
        assert jira.format_bullet_list(None) == ""

    def test_format_bullet_list_with_placeholder(self):
        """Test empty list with placeholder returns placeholder."""
        result = jira.format_bullet_list([], "No items")
        assert result == "* No items"

    def test_format_bullet_list_none_with_placeholder(self):
        """Test None with placeholder returns placeholder."""
        result = jira.format_bullet_list(None, "No items")
        assert result == "* No items"

    def test_format_bullet_list_simple(self):
        """Test simple list formatting."""
        result = jira.format_bullet_list(["item1", "item2"])
        assert result == "* item1\n* item2"

    def test_format_bullet_list_preserves_existing_bullets(self):
        """Test existing bullets are preserved."""
        result = jira.format_bullet_list(["* item1", "item2"])
        assert "* item1" in result
        assert "* item2" in result

    def test_format_bullet_list_preserves_headings(self):
        """Test headings are preserved."""
        result = jira.format_bullet_list(["h3. Heading", "item1"])
        assert "h3. Heading" in result
        assert "* item1" in result

    def test_format_bullet_list_preserves_numbered_items(self):
        """Test numbered items are preserved."""
        result = jira.format_bullet_list(["1. First", "item"])
        assert "1. First" in result
        assert "* item" in result

    def test_format_bullet_list_preserves_hash_headings(self):
        """Test # headings are preserved."""
        result = jira.format_bullet_list(["# Heading", "item"])
        assert "# Heading" in result

    def test_format_bullet_list_skips_empty_items(self):
        """Test empty items are skipped."""
        result = jira.format_bullet_list(["item1", "", "  ", "item2"])
        lines = result.split("\n")
        assert len(lines) == 2
        assert "* item1" in result
        assert "* item2" in result

    def test_format_bullet_list_strips_whitespace(self):
        """Test whitespace is stripped from items."""
        result = jira.format_bullet_list(["  item1  ", "  item2  "])
        assert "* item1" in result
        assert "* item2" in result

    def test_format_bullet_list_all_empty_with_placeholder(self):
        """Test all empty items with placeholder returns placeholder."""
        result = jira.format_bullet_list(["", "  "], "No items")
        assert result == "* No items"

