"""Tests for agentic_devtools.state.update_workflow_step."""

from unittest.mock import patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


def test_update_workflow_step(temp_state_dir):
    """Test update_workflow_step updates the step."""
    state.set_workflow_state(
        name="test-workflow",
        status="in-progress",
        step="step-1",
    )

    state.update_workflow_step("step-2")

    workflow = state.get_workflow_state()
    assert workflow["step"] == "step-2"
    assert workflow["status"] == "in-progress"


def test_update_workflow_step_with_status(temp_state_dir):
    """Test update_workflow_step updates both step and status."""
    state.set_workflow_state(name="test-workflow", status="initiated")

    state.update_workflow_step("step-1", status="in-progress")

    workflow = state.get_workflow_state()
    assert workflow["step"] == "step-1"
    assert workflow["status"] == "in-progress"


def test_update_workflow_step_raises_when_no_workflow(temp_state_dir):
    """Test update_workflow_step raises ValueError when no workflow active."""
    with pytest.raises(ValueError, match="No workflow is currently active"):
        state.update_workflow_step("step-1")
