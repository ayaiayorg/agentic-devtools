"""Tests for _escape_single_quote helper."""

from agentic_devtools.cli.config.commit_type_resolution import _escape_single_quote


class TestEscapeSingleQuote:
    """Tests for _escape_single_quote()."""

    def test_no_special_chars(self):
        """Plain string passes through unchanged."""
        assert _escape_single_quote("feat") == "feat"

    def test_single_quote_escaped(self):
        """Single quotes are escaped with backslash."""
        assert _escape_single_quote("it's") == "it\\'s"

    def test_backslash_escaped_first(self):
        """Backslashes are escaped before single quotes."""
        assert _escape_single_quote("a\\b") == "a\\\\b"

    def test_backslash_then_quote(self):
        """Backslash followed by quote: both escaped in correct order."""
        assert _escape_single_quote("a\\'b") == "a\\\\\\'b"

    def test_empty_string(self):
        """Empty string returns empty."""
        assert _escape_single_quote("") == ""

    def test_multiple_quotes(self):
        """Multiple single quotes are all escaped."""
        assert _escape_single_quote("a'b'c") == "a\\'b\\'c"
