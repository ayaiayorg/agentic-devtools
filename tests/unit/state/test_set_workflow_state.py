"""Tests for SetWorkflowState."""

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
