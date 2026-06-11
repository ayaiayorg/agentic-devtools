"""Tests for extract_title function."""

from agentic_devtools.cli.git.commit_body import extract_title


class TestExtractTitle:
    """Tests for extract_title."""

    def test_single_line_message(self):
        """Test single-line message returns itself."""
        assert extract_title("feat: add webhook") == "feat: add webhook"

    def test_multiline_message_returns_first_line(self):
        """Test multiline message returns only the first line."""
        message = "feat: add webhook\n\n- detail 1\n- detail 2"
        assert extract_title(message) == "feat: add webhook"

    def test_strips_trailing_whitespace(self):
        """Test trailing whitespace on first line is stripped."""
        assert extract_title("title with spaces   ") == "title with spaces"

    def test_empty_string(self):
        """Test empty string returns empty string."""
        assert extract_title("") == ""

    def test_message_with_only_newlines(self):
        """Test message with leading newline."""
        assert extract_title("\nsecond line") == ""
