"""Tests for render_attribution_line function."""

from agentic_devtools.cli.azure_devops.review_attribution import render_attribution_line


class TestRenderAttributionLine:
    """Tests for render_attribution_line."""

    def test_full_attribution_line(self):
        """Test full attribution line rendered with all parameters."""
        result = render_attribution_line(
            model_name="Claude Opus 4.6",
            commit_hash="abc1234def",
            commit_url="https://dev.azure.com/org/proj/_git/repo/pullRequest/1?_a=files",
        )
        assert result == (
            "🤖 *Reviewed by* 🧠 **Claude Opus 4.6** *at commit:* "
            "[`abc1234`](https://dev.azure.com/org/proj/_git/repo/pullRequest/1?_a=files)"
        )

    def test_commit_hash_truncated_to_seven_chars(self):
        """Test that only the first 7 characters of the commit hash are used."""
        result = render_attribution_line(
            model_name="Claude Opus 4.6",
            commit_hash="abcdef1234567890",
            commit_url="https://example.com",
        )
        assert "[`abcdef1`]" in result

    def test_short_commit_hash_used_as_is_if_shorter_than_seven(self):
        """Test that a hash shorter than 7 chars is used completely."""
        result = render_attribution_line(
            model_name="Claude Opus 4.6",
            commit_hash="abc",
            commit_url="https://example.com",
        )
        assert "[`abc`]" in result

    def test_model_name_none_returns_empty_string(self):
        """Test that None model_name returns an empty string."""
        result = render_attribution_line(
            model_name=None,
            commit_hash="abc1234",
            commit_url="https://example.com",
        )
        assert result == ""

    def test_commit_hash_none_returns_empty_string(self):
        """Test that None commit_hash returns an empty string."""
        result = render_attribution_line(
            model_name="Claude Opus 4.6",
            commit_hash=None,
            commit_url="https://example.com",
        )
        assert result == ""

    def test_both_none_returns_empty_string(self):
        """Test that both None model_name and commit_hash returns empty string."""
        result = render_attribution_line(model_name=None, commit_hash=None, commit_url=None)
        assert result == ""

    def test_uses_model_family_icon_auto_detected(self):
        """Test that the model family icon is auto-detected from model_name."""
        result = render_attribution_line(
            model_name="GPT-4o",
            commit_hash="abc1234",
            commit_url="https://example.com",
        )
        assert "🔮" in result

    def test_explicit_model_icon_overrides_auto_detection(self):
        """Test that an explicit model_icon overrides the auto-detected one."""
        result = render_attribution_line(
            model_name="Claude Opus 4.6",
            commit_hash="abc1234",
            commit_url="https://example.com",
            model_icon="🔮",
        )
        assert "🔮 **Claude Opus 4.6**" in result
        assert "🧠" not in result

    def test_generic_robot_icon_always_present(self):
        """Test that the generic 🤖 icon is always present in the line."""
        result = render_attribution_line(
            model_name="Claude Opus 4.6",
            commit_hash="abc1234",
            commit_url="https://example.com",
        )
        assert result.startswith("🤖")

    def test_commit_url_none_renders_bare_hash(self):
        """Test that a None commit_url renders the hash as bare code (no link)."""
        result = render_attribution_line(
            model_name="Claude Opus 4.6",
            commit_hash="abc1234",
            commit_url=None,
        )
        assert "`abc1234`" in result
        assert "](" not in result

    def test_unknown_model_uses_generic_icon(self):
        """Test that an unknown model uses the generic 🤖 icon as family icon."""
        result = render_attribution_line(
            model_name="Llama-3",
            commit_hash="abc1234",
            commit_url="https://example.com",
        )
        # Both the prefix and family icon should be 🤖
        assert "🤖 *Reviewed by* 🤖 **Llama-3**" in result

    def test_model_name_bold_in_output(self):
        """Test that the model name is rendered in bold."""
        result = render_attribution_line(
            model_name="Claude Opus 4.6",
            commit_hash="abc1234",
            commit_url="https://example.com",
        )
        assert "**Claude Opus 4.6**" in result

    def test_markdown_special_chars_in_model_name_are_escaped(self):
        """Test that markdown-sensitive characters in model_name are backslash-escaped."""
        result = render_attribution_line(
            model_name="My*Model_v2",
            commit_hash="abc1234",
            commit_url="https://example.com",
        )
        assert r"My\*Model\_v2" in result
        # The escaped name should still be inside bold markers
        assert r"**My\*Model\_v2**" in result
