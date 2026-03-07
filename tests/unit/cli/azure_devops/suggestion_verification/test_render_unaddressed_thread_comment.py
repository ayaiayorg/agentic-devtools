"""Tests for render_unaddressed_thread_comment function."""

from agentic_devtools.cli.azure_devops.suggestion_verification import render_unaddressed_thread_comment


class TestRenderUnaddressedThreadComment:
    """Tests for render_unaddressed_thread_comment."""

    def test_contains_hash(self):
        result = render_unaddressed_thread_comment("abc1234")
        assert "abc1234" in result
        assert "⚠️ **Unaddressed Suggestion**" in result

    def test_contains_instructions(self):
        result = render_unaddressed_thread_comment("abc1234")
        assert "Make the suggested changes" in result
        assert "Reply to this thread" in result
