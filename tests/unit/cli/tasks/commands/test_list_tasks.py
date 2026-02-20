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


class TestListTasks:
    """Tests for list_tasks command."""

    def test_list_tasks_empty(self, mock_state_dir, capsys):
        """Test list_tasks with no tasks."""
        list_tasks()

        captured = capsys.readouterr()
        assert "No background tasks found" in captured.out

    def test_list_tasks_shows_tasks(self, mock_state_dir, capsys):
        """Test list_tasks displays tasks."""
        task1 = _create_and_add_task("agdt-cmd-1")
        task2 = _create_and_add_task("agdt-cmd-2")

        # Mark task1 as completed
        task1.mark_completed(exit_code=0)
        update_task(task1)

        list_tasks()

        captured = capsys.readouterr()
        assert task1.id in captured.out
        assert task2.id in captured.out
        assert "agdt-cmd-1" in captured.out
        assert "agdt-cmd-2" in captured.out

    def test_list_tasks_shows_status(self, mock_state_dir, capsys):
        """Test list_tasks shows task status."""
        task = _create_and_add_task("agdt-test-cmd")
        task.mark_running()
        update_task(task)

        list_tasks()

        captured = capsys.readouterr()
        assert "running" in captured.out.lower()
