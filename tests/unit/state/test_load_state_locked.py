"""Tests for agentic_devtools.state.load_state_locked."""

from agentic_devtools import state


def test_load_state_locked(temp_state_dir):
    """Test load_state_locked returns current state."""
    state.save_state({"key": "value"})

    loaded = state.load_state_locked()
    assert loaded == {"key": "value"}
