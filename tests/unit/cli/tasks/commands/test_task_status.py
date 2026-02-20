"""
Tests for CLI task monitoring commands.

Tests the task monitoring CLI commands that use the actual task_state API:
- BackgroundTask.create + add_task (not create_task)
- update_task (not update_task_status)
- get_background_tasks (returns list, not dict)
- task.id (not task.task_id)
- task.start_time (not task.created_at)
"""

from unittest.mock import patch

import pytest

from agdt_ai_helpers.cli.tasks.commands import (
    task_status,
)
from agdt_ai_helpers.task_state import (
    BackgroundTask,
    add_task,
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


class TestTaskStatus:
    """Tests for task_status command."""

    def test_task_status_no_task_id(self, mock_state_dir, capsys):
        """Test task_status with no task_id in state."""
        # Patch load_state where it's imported from (state module)
        with patch("agdt_ai_helpers.state.load_state", return_value={}):
            with pytest.raises(SystemExit):
                task_status()

        captured = capsys.readouterr()
        assert "No task ID" in captured.out or "background.task_id" in captured.out

    def test_task_status_shows_details(self, mock_state_dir, capsys):
        """Test task_status shows task details."""
        task = _create_and_add_task("agdt-status-test")
        task.mark_completed(exit_code=0)
        update_task(task)

        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": task.id}}):
            task_status()

        captured = capsys.readouterr()
        assert task.id in captured.out
        assert "completed" in captured.out.lower()

    def test_task_status_nonexistent_task(self, mock_state_dir, capsys):
        """Test task_status with non-existent task ID."""
        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": "nonexistent"}}):
            with pytest.raises(SystemExit):
                task_status()

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()
