"""
Tests for task_state module.
"""

from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from agentic_devtools.task_state import (
    BackgroundTask,
    TaskStatus,
    _sort_tasks,
    add_task,
    get_active_tasks,
    get_background_tasks,
    get_failed_most_recent_per_command,
    get_most_recent_tasks_per_command,
    get_task_by_id,
    get_tasks_by_status,
    remove_task,
    update_task,
)


class TestBackgroundTask:
    """Tests for BackgroundTask dataclass."""

    def test_create_task_via_factory(self):
        """Test creating a BackgroundTask via factory method."""
        task = BackgroundTask.create(
            command="agdt-test-cmd",
            log_file=Path("/path/to/log.txt"),
            args={"key": "value"},
        )
        assert task.command == "agdt-test-cmd"
        assert task.status == TaskStatus.PENDING
        # Path gets normalized by str(), so check it ends with the filename
        assert task.log_file is not None
        assert task.log_file.endswith("log.txt")
        assert task.args == {"key": "value"}
        assert task.end_time is None
        assert task.exit_code is None
        # ID should be a UUID
        assert len(task.id) == 36

    def test_create_task_dataclass_directly(self):
        """Test creating a BackgroundTask directly."""
        task = BackgroundTask(
            id="test-123",
            command="agdt-test-cmd",
            status=TaskStatus.PENDING,
            start_time="2024-01-01T00:00:00+00:00",
            log_file="/path/to/log.txt",
        )
        assert task.id == "test-123"
        assert task.command == "agdt-test-cmd"
        assert task.status == TaskStatus.PENDING
        assert task.log_file == "/path/to/log.txt"
        assert task.end_time is None
        assert task.exit_code is None

    def test_task_to_dict(self):
        """Test converting task to dictionary."""
        task = BackgroundTask(
            id="test-456",
            command="agdt-another-cmd",
            status=TaskStatus.RUNNING,
            start_time="2024-01-01T12:00:00+00:00",
            log_file="/tmp/log.txt",
        )
        task_dict = task.to_dict()

        assert task_dict["id"] == "test-456"
        assert task_dict["command"] == "agdt-another-cmd"
        assert task_dict["status"] == "running"
        assert task_dict["logFile"] == "/tmp/log.txt"
        assert task_dict["startTime"] == "2024-01-01T12:00:00+00:00"

    def test_task_from_dict(self):
        """Test creating task from dictionary."""
        data = {
            "id": "from-dict-789",
            "command": "agdt-cmd",
            "status": "completed",
            "startTime": "2024-01-01T00:00:00+00:00",
            "logFile": "/log.txt",
            "endTime": "2024-01-01T00:01:00+00:00",
            "exitCode": 0,
        }
        task = BackgroundTask.from_dict(data)

        assert task.id == "from-dict-789"
        assert task.status == TaskStatus.COMPLETED
        assert task.exit_code == 0
        assert task.end_time == "2024-01-01T00:01:00+00:00"

    def test_task_roundtrip(self):
        """Test task survives dict roundtrip."""
        original = BackgroundTask(
            id="roundtrip-test",
            command="agdt-cmd",
            status=TaskStatus.FAILED,
            start_time="2024-06-15T10:30:00+00:00",
            log_file="/var/log/task.log",
            end_time="2024-06-15T10:31:00+00:00",
            exit_code=1,
        )
        restored = BackgroundTask.from_dict(original.to_dict())

        assert restored.id == original.id
        assert restored.command == original.command
        assert restored.status == original.status
        assert restored.exit_code == original.exit_code

    def test_mark_running(self):
        """Test marking task as running."""
        task = BackgroundTask.create(command="test")
        assert task.status == TaskStatus.PENDING
        task.mark_running()
        assert task.status == TaskStatus.RUNNING

    def test_mark_completed(self):
        """Test marking task as completed."""
        task = BackgroundTask.create(command="test")
        task.mark_completed(exit_code=0)
        assert task.status == TaskStatus.COMPLETED
        assert task.exit_code == 0
        assert task.end_time is not None

    def test_mark_failed(self):
        """Test marking task as failed."""
        task = BackgroundTask.create(command="test")
        task.mark_failed(exit_code=1, error_message="Something went wrong")
        assert task.status == TaskStatus.FAILED
        assert task.exit_code == 1
        assert task.error_message == "Something went wrong"
        assert task.end_time is not None

    def test_is_terminal(self):
        """Test is_terminal for various statuses."""
        task = BackgroundTask.create(command="test")
        assert not task.is_terminal()

        task.mark_running()
        assert not task.is_terminal()

        task.mark_completed()
        assert task.is_terminal()

        task2 = BackgroundTask.create(command="test2")
        task2.mark_failed()
        assert task2.is_terminal()

    def test_is_recent_unfinished(self):
        """Test is_recent returns True for unfinished tasks."""
        task = BackgroundTask.create(command="test")
        assert task.is_recent()

        task.mark_running()
        assert task.is_recent()

    def test_is_recent_just_finished(self):
        """Test is_recent returns True for just-finished tasks."""
        task = BackgroundTask.create(command="test")
        task.mark_completed()
        # Task just finished, should still be recent
        assert task.is_recent()
