"""Tests for agentic_devtools.state.set_pull_request_id."""

from agentic_devtools import state


def test_set_pull_request_id(temp_state_dir):
    """Test setting pull request ID."""
    state.set_pull_request_id(12345)
    assert state.get_value("pull_request_id") == 12345
