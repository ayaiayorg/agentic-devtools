"""Tests for _parse_bool_interactive."""

import argparse

import pytest

from agentic_devtools.cli.workflows.commands import _parse_bool_interactive


class TestParseBoolInteractive:
    """Tests for the _parse_bool_interactive argparse type validator."""

    def test_true_returns_normalised(self):
        """'true' (case-insensitive) returns 'true'."""
        assert _parse_bool_interactive("true") == "true"
        assert _parse_bool_interactive("True") == "true"
        assert _parse_bool_interactive("TRUE") == "true"

    def test_false_returns_normalised(self):
        """'false' (case-insensitive) returns 'false'."""
        assert _parse_bool_interactive("false") == "false"
        assert _parse_bool_interactive("False") == "false"
        assert _parse_bool_interactive("FALSE") == "false"

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace is stripped."""
        assert _parse_bool_interactive(" true ") == "true"
        assert _parse_bool_interactive("  false  ") == "false"

    def test_invalid_value_raises(self):
        """Invalid values raise ArgumentTypeError."""
        with pytest.raises(argparse.ArgumentTypeError, match="invalid value 'flase'"):
            _parse_bool_interactive("flase")

    def test_numeric_value_raises(self):
        """Numeric values like '0' or '1' raise ArgumentTypeError."""
        with pytest.raises(argparse.ArgumentTypeError, match="must be 'true' or 'false'"):
            _parse_bool_interactive("0")

    def test_yes_no_raises(self):
        """'yes'/'no' are not accepted — only 'true'/'false'."""
        with pytest.raises(argparse.ArgumentTypeError):
            _parse_bool_interactive("yes")
        with pytest.raises(argparse.ArgumentTypeError):
            _parse_bool_interactive("no")
