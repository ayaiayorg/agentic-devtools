"""Tests for agentic_devtools.state.get_all_keys."""

from agentic_devtools import state


def test_get_all_keys(temp_state_dir):
    """Test getting all keys in state."""
    state.set_value("key1", "value1")
    state.set_value("key2", "value2")
    keys = state.get_all_keys()
    assert set(keys) == {"key1", "key2"}
