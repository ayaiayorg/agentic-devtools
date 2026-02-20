"""Tests for agentic_devtools.cli.git.core.get_bool_state."""

from agentic_devtools import state
from agentic_devtools.cli.git import core


class TestGetBoolState:
    """Tests for get_bool_state helper."""

    def test_get_bool_state_true_values(self, temp_state_dir, clear_state_before):
        """Test that truthy values return True."""
        for value in [True, "true", "1", "yes"]:
            state.set_value("test_key", value)
            assert core.get_bool_state("test_key") is True

    def test_get_bool_state_false_values(self, temp_state_dir, clear_state_before):
        """Test that falsy values return False."""
        for value in [False, "false", "0", "no", "", "anything"]:
            state.set_value("test_key", value)
            assert core.get_bool_state("test_key") is False

    def test_get_bool_state_missing_key_default_false(self, temp_state_dir, clear_state_before):
        """Test that missing key returns default False."""
        result = core.get_bool_state("nonexistent_key")
        assert result is False

    def test_get_bool_state_missing_key_custom_default(self, temp_state_dir, clear_state_before):
        """Test that missing key returns custom default."""
        result = core.get_bool_state("nonexistent_key", default=True)
        assert result is True
