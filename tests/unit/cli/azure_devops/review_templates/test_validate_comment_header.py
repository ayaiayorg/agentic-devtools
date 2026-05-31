"""Tests for validate_comment_header utility."""

from agentic_devtools.cli.azure_devops.review_templates import validate_comment_header


class TestValidateCommentHeader:
    """Tests for validate_comment_header."""

    def test_top_level_file_summary_valid(self):
        """Top-level comment with ## File Review Summary: is valid."""
        content = "## File Review Summary: app.py\n\nbody"
        assert validate_comment_header(content, is_subsequent=False) is True

    def test_top_level_overall_summary_valid(self):
        """Top-level comment with ## Overall PR Review Summary is valid."""
        content = "## Overall PR Review Summary\n\nbody"
        assert validate_comment_header(content, is_subsequent=False) is True

    def test_top_level_with_commit_header_invalid(self):
        """Top-level comment with ### Commit: is invalid."""
        content = "### Commit: [abc1234](https://url)\n\nbody"
        assert validate_comment_header(content, is_subsequent=False) is False

    def test_subsequent_with_commit_header_valid(self):
        """Subsequent comment with ### Commit: is valid."""
        content = "### Commit: [abc1234](https://url)\n\nbody"
        assert validate_comment_header(content, is_subsequent=True) is True

    def test_subsequent_with_commit_hash_only_valid(self):
        """Subsequent comment with ### Commit: <hash> (no link) is valid."""
        content = "### Commit: abc1234\n\nbody"
        assert validate_comment_header(content, is_subsequent=True) is True

    def test_subsequent_with_commit_unknown_valid(self):
        """Subsequent comment with ### Commit: unknown is valid."""
        content = "### Commit: unknown\n\nbody"
        assert validate_comment_header(content, is_subsequent=True) is True

    def test_subsequent_with_file_summary_header_invalid(self):
        """Subsequent comment with ## File Review Summary: is invalid."""
        content = "## File Review Summary: app.py\n\nbody"
        assert validate_comment_header(content, is_subsequent=True) is False

    def test_subsequent_with_overall_summary_header_invalid(self):
        """Subsequent comment with ## Overall PR Review Summary is invalid."""
        content = "## Overall PR Review Summary\n\nbody"
        assert validate_comment_header(content, is_subsequent=True) is False

    def test_empty_content_is_invalid(self):
        """Empty content is invalid for both positions."""
        assert validate_comment_header("", is_subsequent=False) is False
        assert validate_comment_header("", is_subsequent=True) is False

    def test_unrecognized_header_invalid_for_both(self):
        """Unrecognized header is invalid for both positions."""
        content = "# Something Else\n\nbody"
        assert validate_comment_header(content, is_subsequent=False) is False
        assert validate_comment_header(content, is_subsequent=True) is False
