"""Tests for agentic_devtools.cli.git.commands._extract_commit_parts."""

from agentic_devtools.cli.git.commands import _extract_commit_parts


class TestExtractCommitParts:
    """Tests for _extract_commit_parts helper."""

    def test_title_only_message(self):
        """Title-only message yields empty body."""
        title, body = _extract_commit_parts("feat(#42): add feature")
        assert title == "feat(#42): add feature"
        assert body == ""

    def test_title_with_blank_separator_and_body(self):
        """Title + blank line + body extracts correctly."""
        msg = "feat(#42): add feature\n\nThis is the body."
        title, body = _extract_commit_parts(msg)
        assert title == "feat(#42): add feature"
        assert body == "This is the body."

    def test_title_with_multiline_body_and_footer(self):
        """Title + blank + multiline body with footer."""
        msg = "feat(#42): add feature\n\n- Item 1\n- Item 2\n\n#42"
        title, body = _extract_commit_parts(msg)
        assert title == "feat(#42): add feature"
        assert body == "- Item 1\n- Item 2\n\n#42"

    def test_title_with_body_no_blank_separator(self):
        """Title + body without blank separator (unusual but valid)."""
        msg = "feat(#42): add feature\nBody without separator"
        title, body = _extract_commit_parts(msg)
        assert title == "feat(#42): add feature"
        assert body == "Body without separator"

    def test_empty_string(self):
        """Empty string yields empty title and empty body."""
        title, body = _extract_commit_parts("")
        assert title == ""
        assert body == ""

    def test_whitespace_preservation(self):
        """Preserves whitespace in title and body (NFR-002)."""
        msg = "  leading spaces  \n\n  body with spaces  \n  line 2  "
        title, body = _extract_commit_parts(msg)
        assert title == "  leading spaces  "
        assert body == "  body with spaces  \n  line 2  "

    def test_special_characters(self):
        """Special characters are preserved in title and body."""
        msg = 'feat(#42): add `code` & "quotes"\n\nBody with (parens) [brackets] {braces}'
        title, body = _extract_commit_parts(msg)
        assert title == 'feat(#42): add `code` & "quotes"'
        assert body == "Body with (parens) [brackets] {braces}"

    def test_only_newline(self):
        """Single newline gives empty title and empty body."""
        title, body = _extract_commit_parts("\n")
        assert title == ""
        assert body == ""

    def test_title_with_multiple_blank_lines_before_body(self):
        """Only one blank separator line is stripped."""
        msg = "title\n\n\nextra blank line before body"
        title, body = _extract_commit_parts(msg)
        assert title == "title"
        # First \n after title splits, remainder is "\n\nextra..."
        # First char is \n so it's stripped, leaving "\nextra..."
        assert body == "\nextra blank line before body"
