"""Tests for rewrite_header_for_subsequent utility."""

from agentic_devtools.cli.azure_devops.review_templates import rewrite_header_for_subsequent


class TestRewriteHeaderForSubsequent:
    """Tests for rewrite_header_for_subsequent."""

    def test_rewrites_file_summary_header_with_hash_and_url(self):
        """Rewrites ## File Review Summary: ... with ### Commit: [hash](url)."""
        content = "## File Review Summary: app.py\n\n*Status:* ✅ Approved"
        result = rewrite_header_for_subsequent(content, "abc1234def5678", "https://commit/url")
        assert result.startswith("### Commit: [abc1234](https://commit/url)")
        assert "*Status:* ✅ Approved" in result

    def test_rewrites_overall_summary_header_with_hash_and_url(self):
        """Rewrites ## Overall PR Review Summary with ### Commit: [hash](url)."""
        content = "## Overall PR Review Summary\n\n*Status:* ⏳ Unreviewed"
        result = rewrite_header_for_subsequent(content, "deadbeef1234", "https://pr/files")
        assert result.startswith("### Commit: [deadbee](https://pr/files)")
        assert "*Status:* ⏳ Unreviewed" in result

    def test_rewrites_with_hash_only_no_url(self):
        """Falls back to ### Commit: <short_hash> when URL is None."""
        content = "## File Review Summary: utils.py\n\nbody"
        result = rewrite_header_for_subsequent(content, "abc1234def", None)
        assert result.startswith("### Commit: abc1234")
        assert "body" in result

    def test_rewrites_with_no_hash_no_url(self):
        """Falls back to ### Commit: unknown when both hash and URL are None."""
        content = "## Overall PR Review Summary\n\nbody"
        result = rewrite_header_for_subsequent(content, None, None)
        assert result.startswith("### Commit: unknown")
        assert "body" in result

    def test_returns_unchanged_when_no_summary_heading(self):
        """Returns content unchanged when first line is not a summary heading."""
        content = "### Some Other Heading\n\nbody"
        result = rewrite_header_for_subsequent(content, "abc1234", "https://url")
        assert result == content

    def test_returns_empty_string_unchanged(self):
        """Returns empty string unchanged."""
        assert rewrite_header_for_subsequent("", "abc", "url") == ""

    def test_preserves_body_content(self):
        """Body content after the header is preserved unchanged."""
        body = "\n*Status:* 📝 Needs Work\n\n### Summary of Changes\nFoo bar"
        content = "## File Review Summary: test.py" + body
        result = rewrite_header_for_subsequent(content, "1234567890", "https://x")
        assert result == "### Commit: [1234567](https://x)" + body

    def test_single_line_content_no_body(self):
        """Handles content that is only the heading with no body."""
        content = "## File Review Summary: solo.py"
        result = rewrite_header_for_subsequent(content, "abcdefg", None)
        assert result == "### Commit: abcdefg"
