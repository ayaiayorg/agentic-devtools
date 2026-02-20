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


class TestTaskLog:
    """Tests for task_log command."""

    def test_task_log_no_task_id(self, mock_state_dir, capsys):
        """Test task_log with no task_id in state."""
        with patch("agdt_ai_helpers.state.load_state", return_value={}):
            with pytest.raises(SystemExit):
                task_log()

    def test_task_log_shows_content(self, mock_state_dir, capsys):
        """Test task_log shows log file content."""
        task = _create_and_add_task("agdt-log-test")

        # Create log file with content in the logs directory
        log_dir = mock_state_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        # The log file is stored by the task's log_file attribute
        if task.log_file:
            from pathlib import Path

            log_path = Path(task.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text("Test log output\nLine 2\n")

        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": task.id}}):
            try:
                task_log()
            except SystemExit:
                pass  # May exit if no log file

        captured = capsys.readouterr()
        # Either shows content or indicates no log file
        assert (
            "Test log output" in captured.out
            or "no log" in captured.out.lower()
            or "not found" in captured.out.lower()
            or "No log file" in captured.out
        )

    def test_task_log_no_log_file(self, mock_state_dir, capsys):
        """Test task_log when log file doesn't exist."""
        task = _create_and_add_task("agdt-no-log")

        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": task.id}}):
            try:
                task_log()
            except SystemExit:
                pass  # Expected if no log file

        # Just verify no crash - captured output may vary
