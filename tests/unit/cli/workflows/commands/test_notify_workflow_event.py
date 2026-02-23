"""Tests for workflow event notifications."""

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows.manager import NotifyEventResult, WorkflowEvent, notify_workflow_event


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


class TestNoWorkflowActive:
    """Tests for notify_workflow_event when no workflow is active."""

    def test_returns_not_triggered_with_no_workflow(self, temp_state_dir, clear_state_before):
        """Returns triggered=False when no workflow state exists."""
        result = notify_workflow_event(WorkflowEvent.CHECKLIST_CREATED)

        assert isinstance(result, NotifyEventResult)
        assert result.triggered is False
        assert result.immediate_advance is False
        assert result.new_step is None

    def test_returns_not_triggered_for_unregistered_workflow(self, temp_state_dir, clear_state_before):
        """Returns triggered=False when the active workflow has no definition in the registry."""
        state.set_workflow_state(
            name="create-jira-issue",
            status="in-progress",
            step="initiate",
            context={},
        )

        result = notify_workflow_event(WorkflowEvent.JIRA_ISSUE_CREATED)

        assert result.triggered is False

    def test_returns_not_triggered_when_event_has_no_matching_transition(
        self, temp_state_dir, clear_state_before
    ):
        """Returns triggered=False when no transition matches the event + step combination."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="planning",
            context={"jira_issue_key": "DFLY-1850"},
        )

        # PR_CREATED event is not valid in the planning step
        result = notify_workflow_event(WorkflowEvent.PR_CREATED)

        assert result.triggered is False


class TestContextUpdates:
    """Tests for notify_workflow_event context_updates parameter."""

    def test_context_updates_are_applied_on_transition(self, temp_state_dir, clear_state_before, capsys):
        """Context updates passed to notify_workflow_event are merged into workflow context."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="checklist-creation",
            context={"jira_issue_key": "DFLY-1850"},
        )

        notify_workflow_event(
            WorkflowEvent.CHECKLIST_CREATED,
            context_updates={"custom_key": "custom_value"},
        )

        workflow = state.get_workflow_state()
        assert workflow["context"].get("custom_key") == "custom_value"

    def test_task_id_recorded_in_events_log(self, temp_state_dir, clear_state_before, capsys):
        """task_id is stored in the events_log when a transition is triggered."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="checklist-creation",
            context={"jira_issue_key": "DFLY-1850"},
        )

        notify_workflow_event(
            WorkflowEvent.CHECKLIST_CREATED,
            task_id="task-abc-123",
        )

        workflow = state.get_workflow_state()
        events_log = workflow["context"].get("events_log", [])
        assert len(events_log) > 0
        last_event = events_log[-1]
        assert last_event["event"] == WorkflowEvent.CHECKLIST_CREATED.value
        assert last_event["task_id"] == "task-abc-123"

    def test_events_log_capped_at_twenty_entries(self, temp_state_dir, clear_state_before):
        """Events log is limited to the 20 most recent entries."""
        existing_events = [
            {"event": "jira_comment_added", "timestamp": "2026-01-01T00:00:00Z", "task_id": None}
            for _ in range(25)
        ]
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="planning",
            context={"jira_issue_key": "DFLY-1850", "events_log": existing_events},
        )

        # Trigger a non-advancing event that still logs (JIRA_COMMENT_ADDED -> checklist-creation)
        notify_workflow_event(WorkflowEvent.JIRA_COMMENT_ADDED)

        workflow = state.get_workflow_state()
        events_log = workflow["context"].get("events_log", [])
        assert len(events_log) <= 20


class TestDeferredTransition:
    """Tests for notify_workflow_event with required_tasks (deferred advancement)."""

    def test_git_commit_created_sets_pending_transition(self, temp_state_dir, clear_state_before):
        """GIT_COMMIT_CREATED in commit step defers advancement via pending_transition."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="commit",
            context={"jira_issue_key": "DFLY-1850"},
        )

        result = notify_workflow_event(
            WorkflowEvent.GIT_COMMIT_CREATED,
            task_id="task-git-456",
        )

        assert result.triggered is True
        # The transition has required_tasks, so it should NOT immediately advance
        assert result.immediate_advance is False
        assert result.new_step is None
        # A pending_transition should be stored in context
        workflow = state.get_workflow_state()
        pending = workflow["context"].get("pending_transition")
        assert pending is not None
        assert pending["to_step"] == "pull-request"
        assert "agdt-git-commit" in pending["required_tasks"]
        assert pending["triggered_by"] == WorkflowEvent.GIT_COMMIT_CREATED.value

    def test_step_does_not_change_when_transition_deferred(self, temp_state_dir, clear_state_before):
        """Workflow step remains unchanged when transition is deferred."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="commit",
            context={"jira_issue_key": "DFLY-1850"},
        )

        notify_workflow_event(WorkflowEvent.GIT_COMMIT_CREATED)

        workflow = state.get_workflow_state()
        assert workflow["step"] == "commit"


class TestPullRequestReviewWorkflow:
    """Tests for notify_workflow_event with the pull-request-review workflow."""

    def test_pr_reviewed_advances_file_review_step(self, temp_state_dir, clear_state_before, capsys):
        """PR_REVIEWED event in file-review step immediately advances back to file-review."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="file-review",
            context={"pull_request_id": "42"},
        )

        result = notify_workflow_event(WorkflowEvent.PR_REVIEWED)

        assert result.triggered is True
        assert result.immediate_advance is True
        assert result.new_step == "file-review"
        workflow = state.get_workflow_state()
        assert workflow["step"] == "file-review"

    def test_pr_reviewed_no_effect_outside_file_review_step(self, temp_state_dir, clear_state_before):
        """PR_REVIEWED event has no effect when not in the file-review step."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="decision",
            context={"pull_request_id": "42"},
        )

        result = notify_workflow_event(WorkflowEvent.PR_REVIEWED)

        assert result.triggered is False
        workflow = state.get_workflow_state()
        assert workflow["step"] == "decision"

    def test_jira_comment_added_advances_work_on_issue_from_planning(
        self, temp_state_dir, clear_state_before, capsys
    ):
        """JIRA_COMMENT_ADDED in planning step immediately advances to checklist-creation."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="planning",
            context={"jira_issue_key": "DFLY-1850"},
        )

        result = notify_workflow_event(WorkflowEvent.JIRA_COMMENT_ADDED)

        assert result.triggered is True
        assert result.immediate_advance is True
        assert result.new_step == "checklist-creation"
        workflow = state.get_workflow_state()
        assert workflow["step"] == "checklist-creation"
