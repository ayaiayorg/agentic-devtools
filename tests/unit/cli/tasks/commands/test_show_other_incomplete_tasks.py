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


class TestShowOtherIncompleteTasks:
    """Tests for show_other_incomplete_tasks command."""

    def test_no_incomplete_tasks(self, mock_state_dir, capsys):
        """Test when no incomplete tasks exist."""
        from agdt_ai_helpers.cli.tasks.commands import show_other_incomplete_tasks

        show_other_incomplete_tasks()

        captured = capsys.readouterr()
        assert "No other recent incomplete background tasks" in captured.out

    def test_shows_incomplete_running_tasks(self, mock_state_dir, capsys):
        """Test shows running tasks."""
        from agdt_ai_helpers.cli.tasks.commands import show_other_incomplete_tasks

        task = _create_and_add_task("agdt-running-cmd")
        task.mark_running()
        update_task(task)

        show_other_incomplete_tasks()

        captured = capsys.readouterr()
        assert "Other incomplete background tasks" in captured.out
        assert "agdt-running-cmd" in captured.out
        assert task.id in captured.out

    def test_excludes_completed_tasks(self, mock_state_dir, capsys):
        """Test excludes completed tasks."""
        from agdt_ai_helpers.cli.tasks.commands import show_other_incomplete_tasks

        running = _create_and_add_task("agdt-running")
        running.mark_running()
        update_task(running)

        completed = _create_and_add_task("agdt-completed")
        completed.mark_running()
        completed.mark_completed(exit_code=0)
        update_task(completed)

        show_other_incomplete_tasks()

        captured = capsys.readouterr()
        assert "agdt-running" in captured.out
        assert "agdt-completed" not in captured.out

    def test_excludes_current_task_id(self, mock_state_dir, capsys):
        """Test excludes current task_id from state."""
        from agdt_ai_helpers.cli.tasks.commands import show_other_incomplete_tasks

        task1 = _create_and_add_task("agdt-cmd-1")
        task1.mark_running()
        update_task(task1)

        task2 = _create_and_add_task("agdt-cmd-2")
        task2.mark_running()
        update_task(task2)

        # Set task1 as current task_id
        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": task1.id}}):
            show_other_incomplete_tasks()

        captured = capsys.readouterr()
        # Should show task2 but not task1
        assert "agdt-cmd-2" in captured.out
        assert task2.id in captured.out
