"""Tests for get_next_workflow_prompt and related functions."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows.manager import (
    NextPromptResult,
    PromptStatus,
    _build_command_hint,
    _check_required_tasks_status,
    _render_failure_prompt,
    _render_waiting_prompt,
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
    state_file = temp_state_dir / "dfly-state.json"
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
        assert "dfly-initiate-work-on-jira-issue-workflow" in result.content

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
        mock_task.command = "dfly-run-tests"
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
        assert "dfly-run-tests" in result.content
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
                    "required_tasks": ["dfly-run-tests"],
                },
                "events_log": [
                    {
                        "event": "TASK_COMPLETED",
                        "command": "dfly-run-tests",
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
        mock_failed_task.command = "dfly-run-tests"
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
        assert "dfly-run-tests" in result.content
        assert "Tests failed" in result.content
        assert result.failed_task_ids == ["task-456"]


class TestRenderWaitingPrompt:
    """Tests for _render_waiting_prompt function."""

    def test_renders_single_pending_task(self):
        """Should render a waiting prompt with single task."""
        mock_task = MagicMock()
        mock_task.id = "task-abc-123-def-456"
        mock_task.command = "dfly-run-tests"
        mock_task.status = MagicMock()
        mock_task.status.value = "running"

        result = _render_waiting_prompt(
            workflow_name="work-on-jira-issue",
            step_name="implementation",
            pending_tasks=[mock_task],
        )

        assert "work-on-jira-issue" in result
        assert "implementation" in result
        assert "dfly-run-tests" in result
        assert "task-abc..." in result
        assert "running" in result
        assert "dfly-get-next-workflow-prompt" in result

    def test_renders_multiple_pending_tasks(self):
        """Should render waiting prompt with multiple tasks."""
        task1 = MagicMock()
        task1.id = "task-111"
        task1.command = "dfly-run-tests"
        task1.status = MagicMock()
        task1.status.value = "running"

        task2 = MagicMock()
        task2.id = "task-222"
        task2.command = "dfly-build"
        task2.status = MagicMock()
        task2.status.value = "pending"

        result = _render_waiting_prompt(
            workflow_name="work-on-jira-issue",
            step_name="implementation",
            pending_tasks=[task1, task2],
        )

        assert "dfly-run-tests" in result
        assert "dfly-build" in result
        assert "running" in result
        assert "pending" in result


class TestRenderFailurePrompt:
    """Tests for _render_failure_prompt function."""

    def test_renders_single_failure(self):
        """Should render failure prompt with single failed task."""
        failed_tasks = [
            {
                "command": "dfly-run-tests",
                "error": "3 tests failed",
                "log_file": "/tmp/test.log",
            }
        ]

        result = _render_failure_prompt(
            workflow_name="work-on-jira-issue",
            step_name="implementation-review",
            failed_tasks=failed_tasks,
        )

        assert "work-on-jira-issue" in result
        assert "implementation-review" in result
        assert "dfly-run-tests" in result
        assert "3 tests failed" in result
        assert "/tmp/test.log" in result
        assert "dfly-task-log" in result

    def test_renders_multiple_failures(self):
        """Should render failure prompt with multiple failed tasks."""
        failed_tasks = [
            {"command": "dfly-run-tests", "error": "Tests failed"},
            {"command": "dfly-lint", "error": "Linting errors"},
        ]

        result = _render_failure_prompt(
            workflow_name="work-on-jira-issue",
            step_name="implementation-review",
            failed_tasks=failed_tasks,
        )

        assert "dfly-run-tests" in result
        assert "dfly-lint" in result
        assert "Tests failed" in result
        assert "Linting errors" in result


class TestCheckRequiredTasksStatus:
    """Tests for _check_required_tasks_status function."""

    def test_no_required_tasks_returns_empty(self):
        """When no required tasks, should return empty list."""
        result = _check_required_tasks_status([], {})
        assert result == []

    def test_successful_task_returns_empty(self):
        """When required task succeeded, should return empty list."""
        context = {
            "events_log": [
                {
                    "event": "TASK_COMPLETED",
                    "command": "dfly-run-tests",
                    "task_id": "task-123",
                    "success": True,
                }
            ]
        }
        result = _check_required_tasks_status(["dfly-run-tests"], context)
        assert result == []

    def test_failed_task_returns_failure_info(self):
        """When required task failed, should return failure info."""
        from agentic_devtools.task_state import TaskStatus

        context = {
            "events_log": [
                {
                    "event": "TASK_COMPLETED",
                    "command": "dfly-run-tests",
                    "task_id": "task-123",
                    "success": False,
                    "error": "Test failures",
                    "log_file": "/tmp/log.txt",
                }
            ]
        }

        # Mock the task returned by get_task_by_id
        mock_failed_task = MagicMock()
        mock_failed_task.id = "task-123"
        mock_failed_task.command = "dfly-run-tests"
        mock_failed_task.status = TaskStatus.FAILED
        mock_failed_task.error_message = "Test failures"
        mock_failed_task.log_file = "/tmp/log.txt"

        with patch(
            "agentic_devtools.cli.workflows.manager.get_task_by_id",
            return_value=mock_failed_task,
        ):
            result = _check_required_tasks_status(["dfly-run-tests"], context)

        assert len(result) == 1
        assert result[0]["command"] == "dfly-run-tests"
        assert result[0]["error"] == "Test failures"
        assert result[0]["log_file"] == "/tmp/log.txt"

    def test_missing_task_not_treated_as_failure(self):
        """When required task has no log entry, should not treat as failure."""
        context = {"events_log": []}
        result = _check_required_tasks_status(["dfly-run-tests"], context)
        # Task not in log means it hasn't completed yet - not a failure
        assert result == []


class TestBuildCommandHint:
    """Tests for _build_command_hint function."""

    def test_with_current_value_shows_truncated_preview(self):
        """When value exists and is long, should truncate for display."""
        long_value = "A" * 150  # Longer than 100 chars

        result = _build_command_hint(
            command_name="dfly-add-jira-comment",
            param_name="--jira-comment",
            state_key="jira.comment",
            current_value=long_value,
            is_required=True,
        )

        assert "--jira-comment" in result
        assert "optional" in result
        assert "..." in result  # Truncated
        assert "dfly-get jira.comment" in result

    def test_with_short_value_shows_full_preview(self):
        """When value exists and is short, should show full value."""
        short_value = "Quick note"

        result = _build_command_hint(
            command_name="dfly-add-jira-comment",
            param_name="--jira-comment",
            state_key="jira.comment",
            current_value=short_value,
            is_required=True,
        )

        assert "--jira-comment" in result
        assert "Quick note" in result
        assert "..." not in result

    def test_without_value_required_shows_required(self):
        """When no value and required, should indicate REQUIRED."""
        result = _build_command_hint(
            command_name="dfly-git-save-work",
            param_name="--commit-message",
            state_key="commit_message",
            current_value=None,
            is_required=True,
        )

        assert "--commit-message" in result
        assert "REQUIRED" in result
        assert "not set" in result

    def test_without_value_optional_shows_optional(self):
        """When no value and optional, should indicate optional."""
        result = _build_command_hint(
            command_name="dfly-git-save-work",
            param_name="--source-branch",
            state_key="source_branch",
            current_value=None,
            is_required=False,
        )

        assert "--source-branch" in result
        assert "optional" in result
        assert "not set" in result

    def test_multiline_value_escaped(self):
        """Newlines in value should be escaped for display."""
        multiline = "Line 1\nLine 2\nLine 3"

        result = _build_command_hint(
            command_name="dfly-add-jira-comment",
            param_name="--jira-comment",
            state_key="jira.comment",
            current_value=multiline,
            is_required=True,
        )

        assert "\\n" in result  # Newlines escaped
        assert "\n" not in result.split('"')[1]  # No actual newlines in the quoted value


class TestNextPromptResult:
    """Tests for NextPromptResult dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        result = NextPromptResult(
            status=PromptStatus.SUCCESS,
            content="Test content",
        )

        assert result.status == PromptStatus.SUCCESS
        assert result.content == "Test content"
        assert result.step is None
        assert result.pending_task_ids is None
        assert result.failed_task_ids is None

    def test_all_fields_set(self):
        """Should store all provided fields."""
        result = NextPromptResult(
            status=PromptStatus.WAITING,
            content="Waiting...",
            step="implementation",
            pending_task_ids=["task-1", "task-2"],
            failed_task_ids=None,
        )

        assert result.step == "implementation"
        assert result.pending_task_ids == ["task-1", "task-2"]


class TestPromptStatus:
    """Tests for PromptStatus enum."""

    def test_all_statuses_defined(self):
        """Should have all expected status values."""
        assert PromptStatus.SUCCESS.value == "success"
        assert PromptStatus.WAITING.value == "waiting"
        assert PromptStatus.FAILURE.value == "failure"
        assert PromptStatus.NO_WORKFLOW.value == "no_workflow"
