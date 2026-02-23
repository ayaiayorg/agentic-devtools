"""Tests for agentic_devtools.state.update_workflow_context."""

import pytest

from agentic_devtools import state


def test_update_workflow_context(temp_state_dir):
    """Test update_workflow_context merges context."""
    state.set_workflow_state(
        name="test-workflow",
        status="in-progress",
        context={"key1": "value1"},
    )

    state.update_workflow_context({"key2": "value2"})

    workflow = state.get_workflow_state()
    assert workflow["context"] == {"key1": "value1", "key2": "value2"}


def test_update_workflow_context_raises_when_no_workflow(temp_state_dir):
    """Test update_workflow_context raises ValueError when no workflow active."""
    with pytest.raises(ValueError, match="No workflow is currently active"):
        state.update_workflow_context({"key": "value"})
