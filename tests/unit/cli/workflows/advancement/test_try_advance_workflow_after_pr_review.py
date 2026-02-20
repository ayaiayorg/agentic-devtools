"""Tests for try advance workflow after pr review."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import advancement


@pytest.fixture
def temp_state_dir(tmp_path):
    """Use a temporary directory for state storage."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


class TestTryAdvanceWorkflowAfterPrReview:
    """Tests for try_advance_workflow_after_pr_review."""

    def test_no_advance_when_no_workflow(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when no workflow is active."""
        result = advancement.try_advance_workflow_after_pr_review()
        assert result is False

    def test_no_advance_when_wrong_workflow(self, temp_state_dir, clear_state_before):
        """Test that nothing happens for a non-PR-review workflow."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
        )
        result = advancement.try_advance_workflow_after_pr_review()
        assert result is False
