"""Tests for WorkflowStateIntegration."""

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


class TestWorkflowStateIntegration:
    """Integration tests for workflow state management."""

    def test_full_workflow_lifecycle(self, temp_state_dir, clear_state_before):
        """Test complete workflow lifecycle: create, update, complete, clear."""
        # Start workflow
        state.set_workflow_state(
            name="pull-request-review",
            status="active",
            step="initiate",
            context={"pull_request_id": "123"},
        )
        assert state.is_workflow_active("pull-request-review") is True

        # Update step
        state.update_workflow_step("reviewing")
        result = state.get_workflow_state()
        assert result["step"] == "reviewing"

        # Update context (merges with existing context)
        state.update_workflow_context({"review_started": True})
        result = state.get_workflow_state()
        assert result["context"]["review_started"] is True
        assert result["context"]["pull_request_id"] == "123"

        # Complete workflow
        state.set_workflow_state(
            name="pull-request-review",
            status="completed",
            step="done",
            context=result["context"],
        )
        # Note: is_workflow_active checks existence, not status - still True
        assert state.is_workflow_active("pull-request-review") is True

        # Clear workflow
        state.clear_workflow_state()
        assert state.get_workflow_state() is None

    def test_workflow_state_isolated_from_regular_state(self, temp_state_dir, clear_state_before):
        """Test that workflow state is isolated from regular state."""
        # Set regular state
        state.set_value("key", "value")

        # Set workflow state
        state.set_workflow_state(name="test", status="active", step="step1")

        # Clear workflow should not affect regular state
        state.clear_workflow_state()
        assert state.get_value("key") == "value"

        # Regular clear_state should clear workflow state too
        state.set_workflow_state(name="test", status="active", step="step1")
        state.clear_state()
        assert state.get_workflow_state() is None
