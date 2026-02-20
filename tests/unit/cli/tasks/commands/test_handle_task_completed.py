"""
Tests for CLI task monitoring commands.

Tests the task monitoring CLI commands that use the actual task_state API:
- BackgroundTask.create + add_task (not create_task)
- update_task (not update_task_status)
- get_background_tasks (returns list, not dict)
- task.id (not task.task_id)
- task.start_time (not task.created_at)
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from agdt_ai_helpers.cli.tasks.commands import (
    list_tasks,
    task_log,
    task_status,
    task_wait,
    tasks_clean,
)
from agdt_ai_helpers.task_state import (
    BackgroundTask,
    add_task,
    get_background_tasks,
    get_task_by_id,
    update_task,
)


@pytest.fixture
def mock_state_dir(tmp_path):
    """Fixture to mock the state directory."""
    # Patch get_state_dir in the state module (where it's defined)
    with patch("agdt_ai_helpers.state.get_state_dir", return_value=tmp_path):
        yield tmp_path


def _create_and_add_task(command: str) -> BackgroundTask:
    """Helper to create and add a task using the real API."""
    task = BackgroundTask.create(command=command)
    add_task(task)
    return task


class TestHandleTaskCompleted:
    """Tests for _handle_task_completed function."""

    def test_shows_failed_task_log(self, mock_state_dir, capsys, tmp_path):
        """Test shows log content when task fails."""
        # Create task with log file
        log_file = tmp_path / "test.log"
        log_file.write_text("Error: Something went wrong\nStack trace here\n")

        task = BackgroundTask.create(command="agdt-test-cmd", log_file=log_file)
        task.mark_running()
        task.mark_failed(exit_code=1)
        task.error_message = "Task execution failed"
        add_task(task)

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "agdt_ai_helpers.task_state.get_incomplete_most_recent_per_command",
                return_value=[],
            ), patch(
                "agdt_ai_helpers.task_state.get_failed_most_recent_per_command",
                return_value=[],
            ):
                from agdt_ai_helpers.cli.tasks.commands import _handle_task_completed

                _handle_task_completed(task, task.id, 300.0)

        assert exc_info.value.code != 0

        captured = capsys.readouterr()
        assert "TASK FAILED" in captured.out
        assert "Error: Something went wrong" in captured.out
        assert "Task execution failed" in captured.out

    def test_reports_other_incomplete_tasks(self, mock_state_dir, capsys):
        """Test reports other incomplete tasks."""
        # Create completed task
        completed_task = _create_and_add_task("agdt-completed-cmd")
        completed_task.mark_running()
        completed_task.mark_completed(exit_code=0)
        update_task(completed_task)

        # Create another incomplete task
        incomplete_task = _create_and_add_task("agdt-incomplete-cmd")
        incomplete_task.mark_running()
        update_task(incomplete_task)

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "agdt_ai_helpers.task_state.get_incomplete_most_recent_per_command",
                return_value=[incomplete_task],
            ), patch(
                "agdt_ai_helpers.task_state.get_failed_most_recent_per_command",
                return_value=[],
            ):
                from agdt_ai_helpers.cli.tasks.commands import _handle_task_completed

                _handle_task_completed(completed_task, completed_task.id, 300.0)

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "OTHER TASKS STILL RUNNING" in captured.out
        assert "agdt-incomplete-cmd" in captured.out

    def test_reports_other_failed_tasks(self, mock_state_dir, capsys):
        """Test reports other failed tasks."""
        # Create completed task
        completed_task = _create_and_add_task("agdt-completed-cmd")
        completed_task.mark_running()
        completed_task.mark_completed(exit_code=0)
        update_task(completed_task)

        # Create another failed task (different command)
        failed_task = _create_and_add_task("agdt-failed-cmd")
        failed_task.mark_running()
        failed_task.mark_failed(exit_code=1)
        update_task(failed_task)

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "agdt_ai_helpers.task_state.get_incomplete_most_recent_per_command",
                return_value=[],
            ), patch(
                "agdt_ai_helpers.task_state.get_failed_most_recent_per_command",
                return_value=[failed_task],
            ):
                from agdt_ai_helpers.cli.tasks.commands import _handle_task_completed

                _handle_task_completed(completed_task, completed_task.id, 300.0)

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "OTHER TASKS FAILED" in captured.out
        assert "agdt-failed-cmd" in captured.out
