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
    task_log,
)
from agdt_ai_helpers.task_state import (
    BackgroundTask,
    add_task,
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


class TestTaskLogLineLimits:
    """Tests for task_log line limit handling."""

    def test_task_log_with_positive_line_limit(self, mock_state_dir, capsys, tmp_path):
        """Test task_log with positive line limit (head mode)."""
        from agdt_ai_helpers.state import set_value

        # Create task with multi-line log file
        log_file = tmp_path / "test.log"
        log_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")

        task = BackgroundTask.create(command="agdt-head-test", log_file=log_file)
        add_task(task)

        # Set state values
        set_value("background.task_id", task.id)
        set_value("background.log_lines", "2")  # Only show first 2 lines

        task_log()

        captured = capsys.readouterr()
        assert "Line 1" in captured.out
        assert "Line 2" in captured.out
        # Lines 3-5 should be excluded by head mode
        assert "Line 5" not in captured.out

    def test_task_log_with_negative_line_limit(self, mock_state_dir, capsys, tmp_path):
        """Test task_log with negative line limit (tail mode)."""
        from agdt_ai_helpers.state import set_value

        # Create task with multi-line log file
        log_file = tmp_path / "test.log"
        log_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")

        task = BackgroundTask.create(command="agdt-tail-test", log_file=log_file)
        add_task(task)

        # Set state values
        set_value("background.task_id", task.id)
        set_value("background.log_lines", "-2")  # Only show last 2 lines

        task_log()

        captured = capsys.readouterr()
        # Should have last 2 lines (Line 4 and Line 5), not first lines
        assert "Line 5" in captured.out or "Line 4" in captured.out
        # Line 1 should be excluded by tail mode
        assert "Line 1" not in captured.out

    def test_task_log_with_invalid_line_limit(self, mock_state_dir, capsys, tmp_path):
        """Test task_log ignores invalid line limit."""
        from agdt_ai_helpers.state import set_value

        # Create task with log file
        log_file = tmp_path / "test.log"
        log_file.write_text("Line 1\nLine 2\nLine 3\n")

        task = BackgroundTask.create(command="agdt-invalid-test", log_file=log_file)
        add_task(task)

        # Set invalid line limit (should be ignored)
        set_value("background.task_id", task.id)
        set_value("background.log_lines", "not-a-number")

        task_log()

        captured = capsys.readouterr()
        # All lines should be shown when limit is invalid
        assert "Line 1" in captured.out
        assert "Line 2" in captured.out
        assert "Line 3" in captured.out

    def test_task_log_nonexistent_task(self, mock_state_dir, capsys):
        """Test task_log with nonexistent task ID."""
        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": "fake-task-id"}}):
            with pytest.raises(SystemExit):
                task_log()

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()
