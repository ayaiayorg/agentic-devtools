"""Tests for UpdateWorkflowStep."""

from unittest.mock import patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state.clear_state()
    yield


class TestUpdateWorkflowStep:
    """Tests for update_workflow_step function."""

    def test_update_workflow_step(self, temp_state_dir, clear_state_before):
        """Test updating workflow step."""
        state.set_workflow_state(name="test", status="active", step="step1")
        state.update_workflow_step("step2")
        result = state.get_workflow_state()
        assert result["step"] == "step2"

    def test_update_workflow_step_preserves_other_fields(self, temp_state_dir, clear_state_before):
        """Test that updating step preserves other workflow fields."""
        state.set_workflow_state(
            name="test",
            status="active",
            step="step1",
            context={"key": "value"},
        )
        state.update_workflow_step("step2")
        result = state.get_workflow_state()
        assert result["active"] == "test"
        assert result["status"] == "active"
        assert result["context"] == {"key": "value"}

    def test_update_workflow_step_when_no_workflow(self, temp_state_dir, clear_state_before):
        """Test updating step when no workflow exists raises error."""
        with pytest.raises(ValueError, match="No workflow is currently active"):
            state.update_workflow_step("step1")
