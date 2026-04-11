"""Tests for validate_content_shape()."""

from agentic_devtools.context_budget import validate_content_shape


class TestValidateContentShape:
    """Verify content shape validation rules."""

    def test_empty_string_returns_false(self):
        assert validate_content_shape("") is False

    def test_whitespace_only_returns_false(self):
        assert validate_content_shape("   \n\t  ") is False

    def test_punctuation_only_returns_false(self):
        assert validate_content_shape("!@#$%^&*()") is False

    def test_fewer_than_3_alphanumeric_returns_false(self):
        assert validate_content_shape("a!") is False
        assert validate_content_shape("ab") is False

    def test_exactly_3_alphanumeric_returns_true(self):
        assert validate_content_shape("abc") is True

    def test_mixed_content_returns_true(self):
        assert validate_content_shape("hello, world!") is True

    def test_numeric_content_returns_true(self):
        assert validate_content_shape("123") is True

    def test_symbols_with_letters(self):
        assert validate_content_shape("a-b-c") is True
