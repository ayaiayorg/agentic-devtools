"""Tests for workflow event notifications."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows.manager import NotifyEventResult, WorkflowEvent, notify_workflow_event


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


class TestChecklistCreatedEvent:
    """Tests for CHECKLIST_CREATED workflow event."""

    def test_advances_from_checklist_creation_to_implementation(self, temp_state_dir, clear_state_before, capsys):
        """Test that CHECKLIST_CREATED event immediately advances to implementation."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="checklist-creation",
            context={"jira_issue_key": "DFLY-1850"},
        )

        result = notify_workflow_event(WorkflowEvent.CHECKLIST_CREATED)

        assert isinstance(result, NotifyEventResult)
        assert result.triggered is True
        # Since CHECKLIST_CREATED has auto_advance=True (default) and no required_tasks,
        # it should immediately advance and render the prompt
        assert result.immediate_advance is True
        assert result.prompt_rendered is True
        assert result.new_step == "implementation"
        workflow = state.get_workflow_state()
        # State should be updated directly (not pending_transition)
        assert workflow["step"] == "implementation"
        # Verify the prompt was printed
        captured = capsys.readouterr()
        assert "WORKFLOW ADVANCED" in captured.out
        assert "implementation" in captured.out

    def test_no_effect_on_wrong_step(self, temp_state_dir, clear_state_before):
        """Test that CHECKLIST_CREATED does nothing when not in checklist-creation step."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="planning",
            context={"jira_issue_key": "DFLY-1850"},
        )

        result = notify_workflow_event(WorkflowEvent.CHECKLIST_CREATED)

        assert result.triggered is False
        workflow = state.get_workflow_state()
        assert "pending_transition" not in workflow.get("context", {})


class TestChecklistCompleteEvent:
    """Tests for CHECKLIST_COMPLETE workflow event."""

    def test_advances_from_implementation_to_review(self, temp_state_dir, clear_state_before, capsys):
        """Test that CHECKLIST_COMPLETE event immediately advances to implementation-review."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1850"},
        )

        result = notify_workflow_event(WorkflowEvent.CHECKLIST_COMPLETE)

        assert isinstance(result, NotifyEventResult)
        assert result.triggered is True
        # Since CHECKLIST_COMPLETE has auto_advance=True and no required_tasks,
        # it should immediately advance and render the prompt
        assert result.immediate_advance is True
        assert result.prompt_rendered is True
        assert result.new_step == "implementation-review"
        workflow = state.get_workflow_state()
        # State should be updated directly (not pending_transition)
        assert workflow["step"] == "implementation-review"
        # Verify the prompt was printed
        captured = capsys.readouterr()
        assert "WORKFLOW ADVANCED" in captured.out
        assert "implementation-review" in captured.out

    def test_no_effect_on_wrong_step(self, temp_state_dir, clear_state_before):
        """Test that CHECKLIST_COMPLETE does nothing when not in implementation step."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="verification",
            context={"jira_issue_key": "DFLY-1850"},
        )

        result = notify_workflow_event(WorkflowEvent.CHECKLIST_COMPLETE)

        assert result.triggered is False
