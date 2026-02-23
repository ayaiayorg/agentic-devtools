"""Tests for _append_terminal_log helper."""

from agentic_devtools.cli.github.issue_commands import _append_terminal_log


class TestAppendTerminalLog:
    """Tests for _append_terminal_log."""

    def test_no_log_returns_body_unchanged(self):
        """Returns body unchanged when terminal_log is None."""
        body = "Original body"
        result = _append_terminal_log(body, None)
        assert result == body

    def test_empty_log_returns_body_unchanged(self):
        """Returns body unchanged when terminal_log is empty string."""
        body = "Original body"
        result = _append_terminal_log(body, "")
        assert result == body

    def test_appends_terminal_output_section(self):
        """Appends Terminal Output section with code block."""
        result = _append_terminal_log("Body", "Error: something went wrong")
        assert "Terminal Output" in result
        assert "Error: something went wrong" in result

    def test_log_wrapped_in_code_block(self):
        """Log content is wrapped in a markdown code block."""
        result = _append_terminal_log("Body", "some output")
        assert "```" in result
