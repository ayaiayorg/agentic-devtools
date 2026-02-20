"""Tests for ClearWorkflowState."""

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
