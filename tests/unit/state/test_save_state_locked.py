"""Tests for agentic_devtools.state.save_state_locked."""

from agentic_devtools import state


def test_save_state_locked(temp_state_dir):
    """Test save_state_locked saves state and returns path."""
    path = state.save_state_locked({"key": "value"})

    assert path.exists()
    loaded = state.load_state()
    assert loaded == {"key": "value"}
