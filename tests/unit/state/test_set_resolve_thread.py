"""Tests for agentic_devtools.state.set_resolve_thread."""

from agentic_devtools import state


def test_set_resolve_thread_true(temp_state_dir):
    """Test setting resolve_thread to True."""
    state.set_resolve_thread(True)
    assert state.should_resolve_thread() is True


def test_set_resolve_thread_false(temp_state_dir):
    """Test setting resolve_thread to False."""
    state.set_resolve_thread(False)
    assert state.should_resolve_thread() is False
