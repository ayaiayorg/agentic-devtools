"""Tests for BackgroundTask.is_expired method."""

from datetime import datetime, timedelta, timezone

from agentic_devtools.task_state import BackgroundTask, TaskStatus


class TestIsExpired:
    """Tests for BackgroundTask.is_expired method."""

    def test_non_terminal_task_is_not_expired(self):
        """A running (non-terminal) task should never be expired."""
        task = BackgroundTask(
            id="test-1",
            command="agdt-test",
            status=TaskStatus.RUNNING,
            start_time=datetime.now(timezone.utc).isoformat(),
            end_time=None,
        )
        assert task.is_expired() is False

    def test_terminal_task_without_end_time_is_not_expired(self):
        """A completed task with no end_time should not be expired."""
        task = BackgroundTask(
            id="test-2",
            command="agdt-test",
            status=TaskStatus.COMPLETED,
            start_time=datetime.now(timezone.utc).isoformat(),
            end_time=None,
        )
        assert task.is_expired() is False

    def test_recently_completed_task_is_not_expired(self):
        """A task completed moments ago should not be expired."""
        task = BackgroundTask(
            id="test-3",
            command="agdt-test",
            status=TaskStatus.COMPLETED,
            start_time=datetime.now(timezone.utc).isoformat(),
        )
        task.mark_completed(exit_code=0)
        assert task.is_expired(retention_hours=24) is False

    def test_old_completed_task_is_expired(self):
        """A task completed more than retention_hours ago should be expired."""
        old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        task = BackgroundTask(
            id="test-4",
            command="agdt-test",
            status=TaskStatus.COMPLETED,
            start_time=old_time,
            end_time=old_time,
        )
        assert task.is_expired(retention_hours=24) is True

    def test_old_failed_task_is_expired(self):
        """A failed task older than retention period should be expired."""
        old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        task = BackgroundTask(
            id="test-5",
            command="agdt-test",
            status=TaskStatus.FAILED,
            start_time=old_time,
            end_time=old_time,
        )
        assert task.is_expired(retention_hours=24) is True
