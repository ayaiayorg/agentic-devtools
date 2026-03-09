"""Tests for _parse_int_field."""

import pytest

from agentic_devtools.cli.azure_devops.review_config import (
    ReviewConfigError,
    _parse_int_field,
)


class TestParseIntField:
    """Tests for _parse_int_field."""

    def test_accepts_plain_int(self):
        """Accepts a plain integer value."""
        assert _parse_int_field("section", "field", 42) == 42

    def test_accepts_zero(self):
        """Accepts zero."""
        assert _parse_int_field("section", "field", 0) == 0

    def test_accepts_negative_int(self):
        """Accepts a negative integer."""
        assert _parse_int_field("section", "field", -1) == -1

    def test_accepts_digit_string(self):
        """Accepts a string of digits."""
        assert _parse_int_field("section", "field", "5") == 5

    def test_accepts_negative_digit_string(self):
        """Accepts a negative number as a string."""
        assert _parse_int_field("section", "field", "-3") == -3

    def test_accepts_negative_zero_string(self):
        """Accepts '-0' as a valid integer string."""
        assert _parse_int_field("section", "field", "-0") == 0

    def test_rejects_bare_minus_string(self):
        """Rejects a bare '-' string."""
        with pytest.raises(ReviewConfigError, match="must be an integer, got string value"):
            _parse_int_field("section", "field", "-")

    def test_rejects_bool_true(self):
        """Rejects boolean True (bool is a subclass of int)."""
        with pytest.raises(ReviewConfigError, match="must be an integer, got boolean value True"):
            _parse_int_field("section", "field", True)

    def test_rejects_bool_false(self):
        """Rejects boolean False."""
        with pytest.raises(ReviewConfigError, match="must be an integer, got boolean value False"):
            _parse_int_field("section", "field", False)

    def test_rejects_float(self):
        """Rejects float values."""
        with pytest.raises(ReviewConfigError, match="must be an integer, got float value"):
            _parse_int_field("section", "field", 1.5)

    def test_rejects_non_numeric_string(self):
        """Rejects non-numeric strings."""
        with pytest.raises(ReviewConfigError, match="must be an integer, got string value"):
            _parse_int_field("section", "field", "abc")

    def test_rejects_none(self):
        """Rejects None values."""
        with pytest.raises(ReviewConfigError, match="must be an integer, got NoneType value"):
            _parse_int_field("section", "field", None)

    def test_rejects_list(self):
        """Rejects list values."""
        with pytest.raises(ReviewConfigError, match="must be an integer, got list value"):
            _parse_int_field("section", "field", [1, 2])

    def test_qualified_name_with_section(self):
        """Error message includes section.field when section is non-empty."""
        with pytest.raises(ReviewConfigError, match="consensus.min_reviewers must be"):
            _parse_int_field("consensus", "min_reviewers", True)

    def test_qualified_name_without_section(self):
        """Error message uses just field name when section is empty."""
        with pytest.raises(ReviewConfigError, match="^version must be"):
            _parse_int_field("", "version", True)
