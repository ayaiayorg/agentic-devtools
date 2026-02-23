"""Tests for agentic_devtools.state.set_thread_id."""

from agentic_devtools import state


def test_set_thread_id(temp_state_dir):
    """Test setting thread ID."""
    state.set_thread_id(67890)
    assert state.get_value("thread_id") == 67890
