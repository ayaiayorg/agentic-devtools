"""Tests for agentic_devtools.skill_injector._derive_fallback_description_from_markdown."""

from agentic_devtools.skill_injector import _derive_fallback_description_from_markdown


class TestDeriveFallbackDescriptionFromMarkdown:
    """Tests for the _derive_fallback_description_from_markdown helper."""

    def test_returns_heading_text_for_h1(self):
        """Returns the text of the first # heading."""
        result = _derive_fallback_description_from_markdown("# My Heading\nBody text")
        assert result == "My Heading"

    def test_returns_heading_text_strips_multiple_hashes(self):
        """Returns heading text stripped of leading hashes for deeper headings."""
        result = _derive_fallback_description_from_markdown("## Sub Heading")
        assert result == "Sub Heading"

    def test_returns_first_non_empty_line_when_no_heading(self):
        """Returns first non-empty line when content has no heading."""
        result = _derive_fallback_description_from_markdown("Some plain text\nMore text")
        assert result == "Some plain text"

    def test_skips_blank_lines_before_heading(self):
        """Skips blank lines and returns first heading found (covers the continue branch)."""
        result = _derive_fallback_description_from_markdown("\n\n# Delayed Heading")
        assert result == "Delayed Heading"

    def test_returns_none_for_empty_content(self):
        """Returns None when content is empty (covers the return None branch)."""
        result = _derive_fallback_description_from_markdown("")
        assert result is None

    def test_returns_none_for_whitespace_only_content(self):
        """Returns None when all lines are whitespace (covers the return None branch)."""
        result = _derive_fallback_description_from_markdown("   \n  \n  ")
        assert result is None

    def test_returns_none_when_heading_has_no_text(self):
        """Returns None when heading line has only # characters (covers the return None branch)."""
        result = _derive_fallback_description_from_markdown("# ")
        assert result is None
