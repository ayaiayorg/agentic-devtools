"""Tests for try advance workflow after pr creation."""

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import advancement


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


class TestTryAdvanceWorkflowAfterPrCreation:
    """Tests for try_advance_workflow_after_pr_creation."""

    def test_no_advance_when_no_workflow(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when no workflow is active."""
        result = advancement.try_advance_workflow_after_pr_creation(12345)
        assert result is False

    def test_no_advance_when_wrong_step(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when not in pull-request step."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="commit",
        )
        result = advancement.try_advance_workflow_after_pr_creation(12345)
        assert result is False

    def test_advances_from_pull_request_to_completion(self, temp_state_dir, clear_state_before):
        """Test that workflow sets pending transition from pull-request to completion.

        The transition has required_tasks=["agdt-create-pull-request"], so the actual step
        change is deferred until get_next_workflow_prompt() is called after the task completes.
        """
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="pull-request",
            context={"jira_issue_key": "DFLY-1850"},
        )

        result = advancement.try_advance_workflow_after_pr_creation(12345, "https://example.com/pr/12345")

        assert result is True
        workflow = state.get_workflow_state()
        # Step remains unchanged until get_next_workflow_prompt is called (has required_tasks)
        assert workflow["step"] == "pull-request"
        # But pending_transition is set
        assert workflow["context"]["pending_transition"]["to_step"] == "completion"
        # And context contains the PR info
        assert workflow["context"]["pull_request_id"] == 12345
        assert workflow["context"]["pull_request_url"] == "https://example.com/pr/12345"
