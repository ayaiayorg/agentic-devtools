"""Tests for agentic_devtools.state.get_value."""

from unittest.mock import patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


class TestGetValue:
    """Tests for get_value function."""

    def test_get_nonexistent_key_returns_none(self, temp_state_dir):
        """Test that getting a nonexistent key returns None."""
        assert state.get_value("nonexistent") is None

    def test_get_required_key_raises_error(self, temp_state_dir):
        """Test that getting a required nonexistent key raises KeyError."""
        with pytest.raises(KeyError, match="Required state key not found"):
            state.get_value("nonexistent", required=True)

    def test_get_existing_string_value(self, temp_state_dir):
        """Test getting an existing string value."""
        state.set_value("test_key", "test_value")
        assert state.get_value("test_key") == "test_value"

    def test_get_integer_value(self, temp_state_dir):
        """Test getting an integer value."""
        state.set_value("count", 42)
        assert state.get_value("count") == 42

    def test_get_float_value(self, temp_state_dir):
        """Test getting a float value."""
        state.set_value("ratio", 3.14)
        assert state.get_value("ratio") == 3.14

    def test_get_boolean_value(self, temp_state_dir):
        """Test getting a boolean value."""
        state.set_value("flag", True)
        assert state.get_value("flag") is True

    def test_get_list_value(self, temp_state_dir):
        """Test getting a list value."""
        items = ["a", "b", "c"]
        state.set_value("items", items)
        assert state.get_value("items") == items

    def test_get_dict_value(self, temp_state_dir):
        """Test getting a dictionary value."""
        config = {"key": "value", "nested": {"inner": 1}}
        state.set_value("config", config)
        assert state.get_value("config") == config
