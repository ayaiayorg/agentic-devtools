"""Tests for agentic_devtools.state.get_pull_request_id."""

from agentic_devtools import state


def test_get_pull_request_id(temp_state_dir):
    """Test getting pull request ID."""
    state.set_pull_request_id(12345)
    assert state.get_pull_request_id() == 12345
