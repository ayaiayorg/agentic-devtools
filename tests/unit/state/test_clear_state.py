"""Tests for agentic_devtools.state.clear_state."""

from agentic_devtools import state


def test_clear_state(temp_state_dir):
    """Test clearing all state."""
    state.set_value("key1", "value1")
    state.set_value("key2", "value2")
    state.clear_state()
    assert state.load_state() == {}
