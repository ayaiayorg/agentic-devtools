"""Tests for collapse_whitespace()."""

from agentic_devtools.context_budget import collapse_whitespace


class TestCollapseWhitespace:
    """Verify whitespace collapsing rules."""

    def test_empty_string(self):
        assert collapse_whitespace("") == ""

    def test_no_extra_whitespace(self):
        text = "Hello world"
        assert collapse_whitespace(text) == text

    def test_multiple_blank_lines_to_single(self):
        text = "line1\n\n\n\nline2"
        result = collapse_whitespace(text)
        assert result == "line1\n\nline2"

    def test_trailing_spaces_removed(self):
        text = "line1   \nline2  "
        result = collapse_whitespace(text)
        assert "   " not in result
        assert result == "line1\nline2"

    def test_multiple_spaces_to_single(self):
        text = "word1    word2"
        result = collapse_whitespace(text)
        assert result == "word1 word2"

    def test_preserves_leading_indent(self):
        text = "    indented line"
        result = collapse_whitespace(text)
        assert result.startswith("    ")

    def test_preserves_single_newlines(self):
        text = "line1\nline2\nline3"
        result = collapse_whitespace(text)
        assert result == "line1\nline2\nline3"

    def test_tabs_in_trailing_whitespace(self):
        text = "line1\t\nline2"
        result = collapse_whitespace(text)
        assert "\t" not in result.split("\n")[0].rstrip("line1")
