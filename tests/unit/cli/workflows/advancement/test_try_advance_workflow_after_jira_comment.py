"""Tests for try_advance_workflow_after_jira_comment."""

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


class TestTryAdvanceWorkflowAfterJiraComment:
    """Tests for try_advance_workflow_after_jira_comment."""

    def test_no_advance_when_no_workflow(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when no workflow is active."""
        result = advancement.try_advance_workflow_after_jira_comment()
        assert result is False

    def test_no_advance_when_different_workflow(self, temp_state_dir, clear_state_before):
        """Test that nothing happens for a different workflow."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="review",
        )
        result = advancement.try_advance_workflow_after_jira_comment()
        assert result is False

    def test_no_advance_when_wrong_step(self, temp_state_dir, clear_state_before):
        """Test that nothing happens when not in planning step."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
        )
        result = advancement.try_advance_workflow_after_jira_comment()
        assert result is False

    def test_advances_from_planning_to_checklist_creation(self, temp_state_dir, clear_state_before, capsys):
        """Test that workflow immediately advances from planning to checklist-creation.

        Since the transition has auto_advance=True (default) and no required_tasks,
        the step change happens immediately and the prompt is rendered.
        """
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="planning",
            context={"jira_issue_key": "DFLY-1850"},
        )

        result = advancement.try_advance_workflow_after_jira_comment()

        assert result is True
        workflow = state.get_workflow_state()
        # Step is immediately updated since no background tasks are required
        assert workflow["step"] == "checklist-creation"
        # Verify prompt was printed
        captured = capsys.readouterr()
        assert "WORKFLOW ADVANCED" in captured.out
        assert "checklist-creation" in captured.out
