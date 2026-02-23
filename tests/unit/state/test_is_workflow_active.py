"""Tests for agentic_devtools.state.is_workflow_active."""

from agentic_devtools import state


def test_is_workflow_active_when_active(temp_state_dir):
    """Test is_workflow_active returns True when workflow is active."""
    state.set_workflow_state(name="test-workflow", status="in-progress")

    assert state.is_workflow_active() is True


def test_is_workflow_active_when_none(temp_state_dir):
    """Test is_workflow_active returns False when no workflow active."""
    assert state.is_workflow_active() is False


def test_is_workflow_active_with_specific_name(temp_state_dir):
    """Test is_workflow_active with specific workflow name."""
    state.set_workflow_state(name="test-workflow", status="in-progress")

    assert state.is_workflow_active("test-workflow") is True
    assert state.is_workflow_active("other-workflow") is False
