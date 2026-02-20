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
    task_wait,
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


class TestTaskWaitValueErrorHandling:
    """Tests for ValueError handling in task_wait argument parsing."""

    def test_task_wait_invalid_timeout_in_state(self, mock_state_dir, capsys):
        """Test task_wait handles invalid timeout value in state."""
        task = _create_and_add_task("agdt-test-cmd")
        task.mark_completed(exit_code=0)
        update_task(task)

        # Set invalid timeout in state
        with patch(
            "agdt_ai_helpers.state.load_state",
            return_value={"background": {"task_id": task.id, "timeout": "not-a-number"}},
        ):
            # Should not crash, uses default timeout
            task_wait()

        captured = capsys.readouterr()
        assert "completed" in captured.out.lower()

    def test_task_wait_invalid_wait_interval_in_state(self, mock_state_dir, capsys):
        """Test task_wait handles invalid wait_interval value in state."""
        task = _create_and_add_task("agdt-test-cmd")
        task.mark_completed(exit_code=0)
        update_task(task)

        # Set invalid wait_interval in state
        with patch(
            "agdt_ai_helpers.state.load_state",
            return_value={"background": {"task_id": task.id, "wait_interval": "invalid"}},
        ):
            # Should not crash, uses default wait interval
            task_wait()

        captured = capsys.readouterr()
        assert "completed" in captured.out.lower()
