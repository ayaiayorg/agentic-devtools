"""Tests for IsWorkflowActive."""

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
