"""Tests for agentic_devtools.state.get_thread_id."""

from agentic_devtools import state


def test_get_thread_id(temp_state_dir):
    """Test getting thread ID."""
    state.set_thread_id(67890)
    assert state.get_thread_id() == 67890
