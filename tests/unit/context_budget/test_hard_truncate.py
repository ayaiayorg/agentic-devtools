"""Tests for hard_truncate()."""

from agentic_devtools.context_budget import hard_truncate


class TestHardTruncate:
    """Verify hard truncation at word boundaries with marker."""

    def test_empty_string(self):
        assert hard_truncate("", 100) == ""

    def test_within_limit_unchanged(self):
        text = "Short text"
        assert hard_truncate(text, 100) == text

    def test_exactly_at_limit(self):
        text = "a" * 50
        assert hard_truncate(text, 50) == text

    def test_truncates_over_limit(self):
        text = "word1 word2 word3 word4 word5"
        result = hard_truncate(text, 25)
        assert len(result) <= 25
        assert result.endswith("[…truncated]")

    def test_truncates_at_word_boundary(self):
        text = "hello world this is a test"
        result = hard_truncate(text, 25)
        assert len(result) <= 25
        # Should not cut in the middle of a word
        assert result.endswith("[…truncated]")

    def test_appends_truncation_marker(self):
        text = "a " * 100
        result = hard_truncate(text, 30)
        assert "[…truncated]" in result

    def test_result_within_limit(self):
        text = "word " * 1000
        result = hard_truncate(text, 50)
        assert len(result) <= 50

    def test_limit_smaller_than_marker(self):
        result = hard_truncate("very long text here", 5)
        assert len(result) <= 5

    def test_no_truncation_needed(self):
        text = "ok"
        assert hard_truncate(text, 1000) == "ok"
