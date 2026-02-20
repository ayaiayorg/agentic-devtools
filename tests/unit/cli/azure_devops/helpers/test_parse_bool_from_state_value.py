"""Tests for parse_bool_from_state helper."""

from agentic_devtools import state
from agentic_devtools.cli import azure_devops


class TestParseBoolFromState:
    """Tests for parse_bool_from_state helper."""

    def test_none_returns_default_false(self, temp_state_dir, clear_state_before):
        """Test None value returns default False."""
        result = azure_devops.parse_bool_from_state("nonexistent")
        assert result is False

    def test_none_returns_custom_default(self, temp_state_dir, clear_state_before):
        """Test None value returns custom default."""
        result = azure_devops.parse_bool_from_state("nonexistent", default=True)
        assert result is True

    def test_bool_true(self, temp_state_dir, clear_state_before):
        """Test boolean True is returned as-is."""
        state.set_value("test_key", True)
        result = azure_devops.parse_bool_from_state("test_key")
        assert result is True

    def test_bool_false(self, temp_state_dir, clear_state_before):
        """Test boolean False is returned as-is."""
        state.set_value("test_key", False)
        result = azure_devops.parse_bool_from_state("test_key")
        assert result is False

    def test_string_true_variations(self, temp_state_dir, clear_state_before):
        """Test various truthy string values."""
        for truthy in ["1", "true", "True", "TRUE", "yes", "Yes", "YES"]:
            state.set_value("test_key", truthy)
            result = azure_devops.parse_bool_from_state("test_key")
            assert result is True, f"Expected True for '{truthy}'"

    def test_string_false_variations(self, temp_state_dir, clear_state_before):
        """Test various falsy string values."""
        for falsy in ["0", "false", "False", "FALSE", "no", "No", "NO", "anything"]:
            state.set_value("test_key", falsy)
            result = azure_devops.parse_bool_from_state("test_key")
            assert result is False, f"Expected False for '{falsy}'"
