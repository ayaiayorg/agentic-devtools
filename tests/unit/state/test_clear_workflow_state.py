"""Tests for agentic_devtools.state.clear_workflow_state."""

from agentic_devtools import state


def test_clear_workflow_state(temp_state_dir):
    """Test clearing workflow state."""
    state.set_workflow_state(name="test-workflow", status="in-progress")
    assert state.get_workflow_state() is not None

    state.clear_workflow_state()
    assert state.get_workflow_state() is None
