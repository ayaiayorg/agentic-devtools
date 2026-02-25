"""Tests for parse_bool_from_state function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.commands import parse_bool_from_state


class TestParseBoolFromState:
    """Tests for parse_bool_from_state function."""

    def test_returns_true_for_true_string(self):
        """Should return True when state contains the string 'true'."""
        with patch(
            "agentic_devtools.cli.azure_devops.commands.get_value",
            return_value="true",
        ):
            result = parse_bool_from_state("some_key")

        assert result is True

    def test_returns_false_for_false_string(self):
        """Should return False when state contains the string 'false'."""
        with patch(
            "agentic_devtools.cli.azure_devops.commands.get_value",
            return_value="false",
        ):
            result = parse_bool_from_state("some_key")

        assert result is False

    def test_returns_default_when_key_not_in_state(self):
        """Should return the default value when the key is not set in state."""
        with patch(
            "agentic_devtools.cli.azure_devops.commands.get_value",
            return_value=None,
        ):
            result = parse_bool_from_state("missing_key", default=True)

        assert result is True

    def test_returns_false_as_default_when_not_specified(self):
        """Should return False as the default when no default arg is given."""
        with patch(
            "agentic_devtools.cli.azure_devops.commands.get_value",
            return_value=None,
        ):
            result = parse_bool_from_state("missing_key")

        assert result is False
