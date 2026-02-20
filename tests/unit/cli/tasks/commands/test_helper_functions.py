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


class TestHelperFunctions:
    """Tests for helper functions in tasks/commands.py."""

    def test_safe_print_with_unicode_error(self, capsys):
        """Test _safe_print handles UnicodeEncodeError gracefully."""
        from agdt_ai_helpers.cli.tasks.commands import _safe_print

        # This should work without raising
        _safe_print("Test with emoji ✅ and text")
        captured = capsys.readouterr()
        assert "Test with emoji" in captured.out

    def test_format_timestamp_with_valid_timestamp(self):
        """Test _format_timestamp with valid ISO timestamp."""
        from agdt_ai_helpers.cli.tasks.commands import _format_timestamp

        ts = "2025-01-15T10:30:00+00:00"
        result = _format_timestamp(ts)
        assert "2025-01-15" in result
        assert "10:30:00" in result

    def test_format_timestamp_with_none(self):
        """Test _format_timestamp with None."""
        from agdt_ai_helpers.cli.tasks.commands import _format_timestamp

        result = _format_timestamp(None)
        assert result == "N/A"

    def test_format_timestamp_with_invalid_timestamp(self):
        """Test _format_timestamp with invalid timestamp string."""
        from agdt_ai_helpers.cli.tasks.commands import _format_timestamp

        result = _format_timestamp("invalid-timestamp")
        assert result == "invalid-timestamp"  # Returns original on error

    def test_format_duration_task_not_started(self, mock_state_dir):
        """Test _format_duration with task that hasn't started."""
        from agdt_ai_helpers.cli.tasks.commands import _format_duration

        task = BackgroundTask.create(command="test-cmd")
        task.start_time = None
        result = _format_duration(task)
        assert result == "Not started"

    def test_format_duration_running_task(self, mock_state_dir):
        """Test _format_duration with running task."""
        from agdt_ai_helpers.cli.tasks.commands import _format_duration

        task = BackgroundTask.create(command="test-cmd")
        task.mark_running()
        # Set start time to 30 seconds ago
        start = datetime.now(timezone.utc) - timedelta(seconds=30)
        task.start_time = start.isoformat()

        result = _format_duration(task)
        assert "s" in result  # Should show seconds

    def test_format_duration_completed_task_minutes(self, mock_state_dir):
        """Test _format_duration with completed task showing minutes."""
        from agdt_ai_helpers.cli.tasks.commands import _format_duration
        from agdt_ai_helpers.task_state import TaskStatus

        task = BackgroundTask.create(command="test-cmd")
        task.status = TaskStatus.COMPLETED
        # Set duration to 2 minutes 30 seconds
        start = datetime.now(timezone.utc) - timedelta(minutes=2, seconds=30)
        task.start_time = start.isoformat()
        task.end_time = datetime.now(timezone.utc).isoformat()

        result = _format_duration(task)
        assert "m" in result  # Should show minutes

    def test_format_duration_completed_task_hours(self, mock_state_dir):
        """Test _format_duration with completed task showing hours."""
        from agdt_ai_helpers.cli.tasks.commands import _format_duration
        from agdt_ai_helpers.task_state import TaskStatus

        task = BackgroundTask.create(command="test-cmd")
        task.status = TaskStatus.COMPLETED
        # Set duration to 1 hour 30 minutes
        start = datetime.now(timezone.utc) - timedelta(hours=1, minutes=30)
        task.start_time = start.isoformat()
        task.end_time = datetime.now(timezone.utc).isoformat()

        result = _format_duration(task)
        assert "h" in result  # Should show hours

    def test_status_indicator_returns_correct_symbols(self):
        """Test _status_indicator returns correct symbols for each status."""
        from agdt_ai_helpers.cli.tasks.commands import _status_indicator
        from agdt_ai_helpers.task_state import TaskStatus

        assert "⏳" in _status_indicator(TaskStatus.PENDING)
        assert "🔄" in _status_indicator(TaskStatus.RUNNING)
        assert "✅" in _status_indicator(TaskStatus.COMPLETED)
        assert "❌" in _status_indicator(TaskStatus.FAILED)
