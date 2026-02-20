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
    list_tasks,
    task_status,
    tasks_clean,
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


class TestTaskCommandIntegration:
    """Integration tests for task commands working together."""

    def test_full_task_monitoring_workflow(self, mock_state_dir, capsys):
        """Test complete workflow: create -> list -> status -> clean."""
        # Create a task
        task = _create_and_add_task("integration-test-cmd")

        # List should show the task
        list_tasks()
        captured = capsys.readouterr()
        assert task.id in captured.out

        # Update to running
        task.mark_running()
        update_task(task)

        # Status should show running
        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": task.id}}):
            task_status()
        captured = capsys.readouterr()
        assert "running" in captured.out.lower()

        # Complete the task
        task.mark_completed(exit_code=0)
        update_task(task)

        # Clean should work without error
        with patch("agdt_ai_helpers.state.load_state", return_value={}):
            tasks_clean()

        # List - task may or may not be removed depending on expiry
        list_tasks()
        captured = capsys.readouterr()
        # Just verify it doesn't crash
