"""Tests for notify_workflow_event function."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.manager import (
    NotifyEventResult,
    WorkflowEvent,
    notify_workflow_event,
)


class TestNotifyWorkflowEvent:
    """Tests for notify_workflow_event function."""

    def test_returns_not_triggered_when_no_workflow_active(self):
        """Should return triggered=False when no workflow is active in state."""
        with patch(
            "agentic_devtools.cli.workflows.manager.get_workflow_state",
            return_value=None,
        ):
            result = notify_workflow_event(WorkflowEvent.MANUAL_ADVANCE)

        assert isinstance(result, NotifyEventResult)
        assert result.triggered is False

    def test_returns_not_triggered_when_workflow_has_no_step(self):
        """Should return triggered=False when workflow is active but has no step."""
        with patch(
            "agentic_devtools.cli.workflows.manager.get_workflow_state",
            return_value={"active": "work-on-jira-issue", "step": None},
        ):
            result = notify_workflow_event(WorkflowEvent.MANUAL_ADVANCE)

        assert result.triggered is False

    def test_returns_not_triggered_for_unknown_workflow(self):
        """Should return triggered=False when workflow definition is not found."""
        with patch(
            "agentic_devtools.cli.workflows.manager.get_workflow_state",
            return_value={"active": "nonexistent-workflow", "step": "some-step"},
        ):
            with patch(
                "agentic_devtools.cli.workflows.manager.get_workflow_definition",
                return_value=None,
            ):
                result = notify_workflow_event(WorkflowEvent.MANUAL_ADVANCE)

        assert result.triggered is False

    def test_returns_notify_event_result_instance(self):
        """Return value should always be a NotifyEventResult instance."""
        with patch(
            "agentic_devtools.cli.workflows.manager.get_workflow_state",
            return_value=None,
        ):
            result = notify_workflow_event(WorkflowEvent.MANUAL_ADVANCE)

        assert isinstance(result, NotifyEventResult)
