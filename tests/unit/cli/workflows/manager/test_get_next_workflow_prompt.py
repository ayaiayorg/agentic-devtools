"""Tests for GetNextWorkflowPrompt."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows.manager import (
    PromptStatus,
    get_next_workflow_prompt,
)


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


class TestGetNextWorkflowPrompt:
    """Tests for get_next_workflow_prompt function."""

    def test_no_workflow_active_returns_no_workflow_status(self, temp_state_dir, clear_state_before):
        """When no workflow is active, should return NO_WORKFLOW status."""
        result = get_next_workflow_prompt()

        assert result.status == PromptStatus.NO_WORKFLOW
        assert "No workflow is currently active" in result.content
        assert "agdt-initiate-work-on-jira-issue-workflow" in result.content

    def test_pending_tasks_returns_waiting_status(self, temp_state_dir, clear_state_before):
        """When there are pending background tasks, should return WAITING status."""
        # Set up a workflow
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
        )

        # Mock pending tasks
        mock_task = MagicMock()
        mock_task.id = "task-123-abc-def"
        mock_task.command = "agdt-run-tests"
        mock_task.status = MagicMock()
        mock_task.status.value = "running"

        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[mock_task],
        ):
            result = get_next_workflow_prompt()

        assert result.status == PromptStatus.WAITING
        assert result.step == "implementation"
        assert "task-123" in result.content
        assert "agdt-run-tests" in result.content
        assert result.pending_task_ids == ["task-123-abc-def"]

    def test_successful_transition_returns_new_step(self, temp_state_dir, clear_state_before):
        """When pending transition exists and tasks passed, should transition to new step."""
        # Set up workflow with pending transition
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="planning",
            context={
                "pending_transition": {
                    "to_step": "implementation",
                    "required_tasks": [],
                },
                "events_log": [],
            },
        )

        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[],
        ), patch(
            "agentic_devtools.cli.workflows.manager._render_step_prompt",
            return_value="# Implementation Step\n\nYour implementation prompt here.",
        ):
            result = get_next_workflow_prompt()

        assert result.status == PromptStatus.SUCCESS
        assert result.step == "implementation"
        assert "Implementation" in result.content

        # Verify workflow state was updated
        workflow = state.get_workflow_state()
        assert workflow["step"] == "implementation"

    def test_transition_to_completion_sets_completed_status(self, temp_state_dir, clear_state_before):
        """When transitioning to completion step, workflow status should be 'completed'."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation-review",
            context={
                "pending_transition": {
                    "to_step": "completion",
                    "required_tasks": [],
                },
                "events_log": [],
            },
        )

        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[],
        ), patch(
            "agentic_devtools.cli.workflows.manager._render_step_prompt",
            return_value="# Workflow Complete\n\nCongratulations!",
        ):
            result = get_next_workflow_prompt()

        assert result.status == PromptStatus.SUCCESS
        assert result.step == "completion"

        workflow = state.get_workflow_state()
        assert workflow["status"] == "completed"

    def test_no_pending_transition_returns_current_step_prompt(self, temp_state_dir, clear_state_before):
        """When no pending transition, should return prompt for current step."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
        )

        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[],
        ), patch(
            "agentic_devtools.cli.workflows.manager._render_step_prompt",
            return_value="# Implementation\n\nContinue implementing.",
        ):
            result = get_next_workflow_prompt()

        assert result.status == PromptStatus.SUCCESS
        assert result.step == "implementation"
        assert "Implementation" in result.content

    def test_prompt_template_not_found_returns_failure(self, temp_state_dir, clear_state_before):
        """When prompt template is missing, should return FAILURE status."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="nonexistent-step",
        )

        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[],
        ), patch(
            "agentic_devtools.cli.workflows.manager._render_step_prompt",
            side_effect=FileNotFoundError("Template not found"),
        ):
            result = get_next_workflow_prompt()

        assert result.status == PromptStatus.FAILURE
        assert "Could not load prompt template" in result.content
        assert result.step == "nonexistent-step"

    def test_failed_required_tasks_returns_failure(self, temp_state_dir, clear_state_before):
        """When required tasks failed, should return FAILURE status."""
        from agentic_devtools.task_state import TaskStatus

        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation-review",
            context={
                "pending_transition": {
                    "to_step": "completion",
                    "required_tasks": ["agdt-run-tests"],
                },
                "events_log": [
                    {
                        "event": "TASK_COMPLETED",
                        "command": "agdt-run-tests",
                        "task_id": "task-456",
                        "success": False,
                        "error": "Tests failed with 3 errors",
                    }
                ],
            },
        )

        # Mock a failed task returned by get_task_by_id
        mock_failed_task = MagicMock()
        mock_failed_task.id = "task-456"
        mock_failed_task.command = "agdt-run-tests"
        mock_failed_task.status = TaskStatus.FAILED
        mock_failed_task.error_message = "Tests failed with 3 errors"
        mock_failed_task.log_file = "/tmp/test.log"

        with patch(
            "agentic_devtools.cli.workflows.manager.get_active_tasks",
            return_value=[],
        ), patch(
            "agentic_devtools.cli.workflows.manager.get_task_by_id",
            return_value=mock_failed_task,
        ):
            result = get_next_workflow_prompt()

        assert result.status == PromptStatus.FAILURE
        assert "agdt-run-tests" in result.content
        assert "Tests failed" in result.content
        assert result.failed_task_ids == ["task-456"]
