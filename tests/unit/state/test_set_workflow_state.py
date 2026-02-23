"""Tests for agentic_devtools.state.set_workflow_state."""

from agentic_devtools import state


class TestSetWorkflowState:
    """Tests for set_workflow_state function."""

    def test_set_and_get_workflow_state(self, temp_state_dir):
        """Test setting and getting workflow state."""
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

    def test_set_workflow_state_preserves_started_at(self, temp_state_dir):
        """Test that updating workflow preserves original started_at."""
        state.set_workflow_state(name="test-workflow", status="initiated")
        original_started = state.get_workflow_state()["started_at"]

        state.set_workflow_state(name="test-workflow", status="in-progress")
        updated_started = state.get_workflow_state()["started_at"]

        assert original_started == updated_started

    def test_set_workflow_state_merges_context(self, temp_state_dir):
        """Test that context is merged when updating same workflow."""
        state.set_workflow_state(
            name="test-workflow",
            status="initiated",
            context={"key1": "value1"},
        )

        state.set_workflow_state(
            name="test-workflow",
            status="in-progress",
            context={"key2": "value2"},
        )

        workflow = state.get_workflow_state()
        assert workflow["context"] == {"key1": "value1", "key2": "value2"}

    def test_set_workflow_state_context_none_removal(self, temp_state_dir):
        """Test that None values in context remove keys."""
        state.set_workflow_state(
            name="test-workflow",
            status="initiated",
            context={"key1": "value1", "key2": "value2"},
        )

        state.set_workflow_state(
            name="test-workflow",
            status="in-progress",
            context={"key1": None, "key3": "value3"},
        )

        workflow = state.get_workflow_state()
        assert "key1" not in workflow["context"]
        assert workflow["context"]["key2"] == "value2"
        assert workflow["context"]["key3"] == "value3"
