"""Tests for try advance workflow after jira issue retrieved."""

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


class TestTryAdvanceWorkflowAfterJiraIssueRetrieved:
    """Tests for try_advance_workflow_after_jira_issue_retrieved."""

    def test_no_advance_when_no_workflow(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when no workflow is active."""
        result = advancement.try_advance_workflow_after_jira_issue_retrieved()
        assert result is False

    def test_no_advance_when_wrong_step(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when not in initiate step."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
        )
        result = advancement.try_advance_workflow_after_jira_issue_retrieved()
        assert result is False

    def test_advances_from_initiate_to_planning(self, temp_state_dir, clear_state_before, capsys):
        """Test that workflow advances from initiate to planning."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="initiate",
            context={"jira_issue_key": "DFLY-1850"},
        )

        issue_data = {
            "fields": {
                "summary": "Test issue summary",
                "issuetype": {"name": "Story"},
                "labels": ["backend", "feature"],
                "description": "Test description",
            }
        }

        result = advancement.try_advance_workflow_after_jira_issue_retrieved(issue_data=issue_data)

        assert result is True
        workflow = state.get_workflow_state()
        # Check context was updated with issue data
        assert workflow["context"]["issue_summary"] == "Test issue summary"
        assert workflow["context"]["issue_type"] == "Story"
        assert workflow["context"]["issue_labels"] == "backend, feature"
