"""Tests for CheckRequiredTasksStatus."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.workflows.manager import (
    _check_required_tasks_status,
)


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


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
                    "command": "agdt-run-tests",
                    "task_id": "task-123",
                    "success": True,
                }
            ]
        }
        result = _check_required_tasks_status(["agdt-run-tests"], context)
        assert result == []

    def test_failed_task_returns_failure_info(self):
        """When required task failed, should return failure info."""
        from agentic_devtools.task_state import TaskStatus

        context = {
            "events_log": [
                {
                    "event": "TASK_COMPLETED",
                    "command": "agdt-run-tests",
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
        mock_failed_task.command = "agdt-run-tests"
        mock_failed_task.status = TaskStatus.FAILED
        mock_failed_task.error_message = "Test failures"
        mock_failed_task.log_file = "/tmp/log.txt"

        with patch(
            "agentic_devtools.cli.workflows.manager.get_task_by_id",
            return_value=mock_failed_task,
        ):
            result = _check_required_tasks_status(["agdt-run-tests"], context)

        assert len(result) == 1
        assert result[0]["command"] == "agdt-run-tests"
        assert result[0]["error"] == "Test failures"
        assert result[0]["log_file"] == "/tmp/log.txt"

    def test_missing_task_not_treated_as_failure(self):
        """When required task has no log entry, should not treat as failure."""
        context = {"events_log": []}
        result = _check_required_tasks_status(["agdt-run-tests"], context)
        # Task not in log means it hasn't completed yet - not a failure
        assert result == []
