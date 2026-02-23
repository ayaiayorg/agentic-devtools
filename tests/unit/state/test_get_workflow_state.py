"""Tests for agentic_devtools.state.get_workflow_state."""

from agentic_devtools import state


def test_get_workflow_state_when_none(temp_state_dir):
    """Test get_workflow_state returns None when no workflow active."""
    assert state.get_workflow_state() is None


def test_get_workflow_state_returns_active_workflow(temp_state_dir):
    """Test get_workflow_state returns active workflow state."""
    state.set_workflow_state(
        name="test-workflow",
        status="in-progress",
        step="step-1",
        context={"key": "value"},
    )

    workflow = state.get_workflow_state()
    assert workflow["active"] == "test-workflow"
    assert workflow["status"] == "in-progress"
    assert workflow["step"] == "step-1"
    assert workflow["context"] == {"key": "value"}
    assert "started_at" in workflow
