"""Tests for assemble_message function."""

from agentic_devtools.cli.git.commit_body import assemble_message


class TestAssembleMessage:
    """Tests for assemble_message."""

    def test_title_and_body(self):
        """Test assembles title + blank line + body."""
        result = assemble_message("feat: add feature", "Body content here")
        assert result == "feat: add feature\n\nBody content here"

    def test_multiline_body(self):
        """Test multiline body is preserved."""
        body = "- item 1\n- item 2\n- item 3"
        result = assemble_message("fix: bug", body)
        assert result == "fix: bug\n\n- item 1\n- item 2\n- item 3"

    def test_blank_line_separator(self):
        """Test there's exactly one blank line between title and body."""
        result = assemble_message("title", "body")
        lines = result.split("\n")
        assert lines[0] == "title"
        assert lines[1] == ""
        assert lines[2] == "body"
