"""Tests for GetWorkflowState."""

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
