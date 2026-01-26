"""
Tests for workflow state management functions.
"""

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


class TestGetWorkflowState:
    """Tests for get_workflow_state function."""

    def test_get_workflow_state_when_not_set(self, temp_state_dir, clear_state_before):
        """Test getting workflow state when no workflow is active."""
        result = state.get_workflow_state()
        assert result is None

    def test_get_workflow_state_when_set(self, temp_state_dir, clear_state_before):
        """Test getting workflow state when workflow is active."""
        state.set_workflow_state(
            name="pull-request-review",
            status="active",
            step="initiate",
            context={"pull_request_id": "123"},
        )
        result = state.get_workflow_state()
        assert result is not None
        assert result["active"] == "pull-request-review"
        assert result["status"] == "active"
        assert result["step"] == "initiate"
        assert result["context"] == {"pull_request_id": "123"}


class TestSetWorkflowState:
    """Tests for set_workflow_state function."""

    def test_set_workflow_state_basic(self, temp_state_dir, clear_state_before):
        """Test setting basic workflow state."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="active",
            step="planning",
        )
        result = state.get_workflow_state()
        assert result["active"] == "work-on-jira-issue"
        assert result["status"] == "active"
        assert result["step"] == "planning"
        # Context may not be present if not provided
        assert result.get("context") is None or result.get("context") == {}

    def test_set_workflow_state_with_context(self, temp_state_dir, clear_state_before):
        """Test setting workflow state with context."""
        context = {
            "jira_issue_key": "DFLY-1234",
            "branch_name": "feature/DFLY-1234/test",
        }
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="active",
            step="implementation",
            context=context,
        )
        result = state.get_workflow_state()
        assert result["context"] == context

    def test_set_workflow_state_overwrites_previous(self, temp_state_dir, clear_state_before):
        """Test that setting workflow state overwrites previous state."""
        state.set_workflow_state(name="workflow1", status="active", step="step1")
        state.set_workflow_state(name="workflow2", status="active", step="step2")
        result = state.get_workflow_state()
        assert result["active"] == "workflow2"
        assert result["step"] == "step2"


class TestClearWorkflowState:
    """Tests for clear_workflow_state function."""

    def test_clear_workflow_state(self, temp_state_dir, clear_state_before):
        """Test clearing workflow state."""
        state.set_workflow_state(name="test", status="active", step="step1")
        state.clear_workflow_state()
        assert state.get_workflow_state() is None

    def test_clear_workflow_state_when_not_set(self, temp_state_dir, clear_state_before):
        """Test clearing workflow state when no workflow is active."""
        # Should not raise any error
        state.clear_workflow_state()
        assert state.get_workflow_state() is None


class TestIsWorkflowActive:
    """Tests for is_workflow_active function."""

    def test_is_workflow_active_false_when_not_set(self, temp_state_dir, clear_state_before):
        """Test is_workflow_active returns False when no workflow exists."""
        assert state.is_workflow_active() is False

    def test_is_workflow_active_true_when_active(self, temp_state_dir, clear_state_before):
        """Test is_workflow_active returns True when workflow is active."""
        state.set_workflow_state(name="test", status="active", step="step1")
        assert state.is_workflow_active() is True

    def test_is_workflow_active_true_when_completed(self, temp_state_dir, clear_state_before):
        """Test is_workflow_active returns True even when workflow is completed (it checks existence, not status)."""
        state.set_workflow_state(name="test", status="completed", step="done")
        # Note: is_workflow_active only checks if a workflow exists, not its status
        assert state.is_workflow_active() is True

    def test_is_workflow_active_true_when_failed(self, temp_state_dir, clear_state_before):
        """Test is_workflow_active returns True even when workflow failed (it checks existence, not status)."""
        state.set_workflow_state(name="test", status="failed", step="error")
        # Note: is_workflow_active only checks if a workflow exists, not its status
        assert state.is_workflow_active() is True

    def test_is_workflow_active_with_specific_name_match(self, temp_state_dir, clear_state_before):
        """Test is_workflow_active with specific workflow name that matches."""
        state.set_workflow_state(name="pull-request-review", status="active", step="step1")
        assert state.is_workflow_active("pull-request-review") is True

    def test_is_workflow_active_with_specific_name_no_match(self, temp_state_dir, clear_state_before):
        """Test is_workflow_active with specific workflow name that doesn't match."""
        state.set_workflow_state(name="pull-request-review", status="active", step="step1")
        assert state.is_workflow_active("work-on-jira-issue") is False


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


class TestUpdateWorkflowContext:
    """Tests for update_workflow_context function."""

    def test_update_workflow_context_add_new_key(self, temp_state_dir, clear_state_before):
        """Test adding new key to workflow context."""
        state.set_workflow_state(name="test", status="active", step="step1")
        state.update_workflow_context({"new_key": "new_value"})
        result = state.get_workflow_state()
        assert result["context"]["new_key"] == "new_value"

    def test_update_workflow_context_update_existing_key(self, temp_state_dir, clear_state_before):
        """Test updating existing key in workflow context."""
        state.set_workflow_state(
            name="test",
            status="active",
            step="step1",
            context={"key": "old_value"},
        )
        state.update_workflow_context({"key": "new_value"})
        result = state.get_workflow_state()
        assert result["context"]["key"] == "new_value"

    def test_update_workflow_context_multiple_keys(self, temp_state_dir, clear_state_before):
        """Test updating multiple keys in workflow context."""
        state.set_workflow_state(name="test", status="active", step="step1")
        state.update_workflow_context({"key1": "value1", "key2": "value2"})
        result = state.get_workflow_state()
        assert result["context"]["key1"] == "value1"
        assert result["context"]["key2"] == "value2"

    def test_update_workflow_context_when_no_workflow(self, temp_state_dir, clear_state_before):
        """Test updating context when no workflow exists raises error."""
        with pytest.raises(ValueError, match="No workflow is currently active"):
            state.update_workflow_context({"key": "value"})

    def test_update_workflow_context_preserves_other_fields(self, temp_state_dir, clear_state_before):
        """Test that updating context preserves other workflow fields."""
        state.set_workflow_state(
            name="test",
            status="active",
            step="step1",
            context={"existing": "value"},
        )
        state.update_workflow_context({"new_key": "new_value"})
        result = state.get_workflow_state()
        assert result["active"] == "test"
        assert result["status"] == "active"
        assert result["step"] == "step1"
        # update_workflow_context merges with existing context
        assert result["context"] == {"existing": "value", "new_key": "new_value"}


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

        # Update context (replaces existing context)
        state.update_workflow_context({"review_started": True})
        result = state.get_workflow_state()
        assert result["context"]["review_started"] is True

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
