"""Tests for UpdateWorkflowContext."""

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
