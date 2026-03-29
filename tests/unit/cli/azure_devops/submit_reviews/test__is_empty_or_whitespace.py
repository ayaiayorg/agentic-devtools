"""Tests for agentic_devtools.cli.azure_devops.submit_reviews._is_empty_or_whitespace."""

from agentic_devtools.cli.azure_devops.submit_reviews import _is_empty_or_whitespace


class TestIsEmptyOrWhitespace:
    """Tests for _is_empty_or_whitespace."""

    def test_none_is_empty(self):
        """None is treated as empty."""
        assert _is_empty_or_whitespace(None) is True

    def test_empty_string_is_empty(self):
        """Empty string is treated as empty."""
        assert _is_empty_or_whitespace("") is True

    def test_whitespace_only_is_empty(self):
        """Whitespace-only string is treated as empty."""
        assert _is_empty_or_whitespace("   ") is True

    def test_non_empty_string_is_not_empty(self):
        """Non-empty string is not treated as empty."""
        assert _is_empty_or_whitespace("hello") is False

    def test_false_is_not_empty(self):
        """False is NOT treated as empty — it should surface as a type error."""
        assert _is_empty_or_whitespace(False) is False

    def test_zero_is_not_empty(self):
        """0 is NOT treated as empty — it should surface as a type error."""
        assert _is_empty_or_whitespace(0) is False

    def test_empty_list_is_not_empty(self):
        """Empty list is NOT treated as empty — it should surface as a type error."""
        assert _is_empty_or_whitespace([]) is False

    def test_empty_dict_is_not_empty(self):
        """Empty dict is NOT treated as empty — it should surface as a type error."""
        assert _is_empty_or_whitespace({}) is False
