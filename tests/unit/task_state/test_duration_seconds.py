"""
Tests for task_state module.
"""

from datetime import timedelta

from agentic_devtools.task_state import (
    BackgroundTask,
    TaskStatus,
)


class TestDurationSeconds:
    """Tests for BackgroundTask.duration_seconds method."""

    def test_completed_task_returns_duration(self):
        """Should return duration for completed task with valid timestamps."""
        task = BackgroundTask(
            id="test",
            command="test",
            status=TaskStatus.COMPLETED,
            start_time="2024-01-01T10:00:00+00:00",
            end_time="2024-01-01T10:05:30+00:00",
        )
        duration = task.duration_seconds()
        assert duration == 5 * 60 + 30  # 5 minutes 30 seconds

    def test_pending_task_returns_none(self):
        """Should return None for pending task without end_time."""
        task = BackgroundTask(
            id="test",
            command="test",
            status=TaskStatus.PENDING,
            start_time="2024-01-01T10:00:00+00:00",
        )
        assert task.duration_seconds() is None

    def test_running_task_returns_current_duration(self):
        """Should return current duration for running task."""
        from datetime import datetime, timezone

        # Start time = 10 seconds ago
        now = datetime.now(timezone.utc)
        start_time = (now.replace(microsecond=0) - timedelta(seconds=10)).isoformat()
        task = BackgroundTask(
            id="test",
            command="test",
            status=TaskStatus.RUNNING,
            start_time=start_time,
        )
        duration = task.duration_seconds()
        assert duration is not None
        # Duration should be approximately 10 seconds (with some tolerance for test execution)
        assert 9 <= duration <= 15

    def test_running_task_with_invalid_start_time(self):
        """Should return None if start_time cannot be parsed."""
        task = BackgroundTask(
            id="test",
            command="test",
            status=TaskStatus.RUNNING,
            start_time="not-a-valid-timestamp",
        )
        assert task.duration_seconds() is None

    def test_completed_task_with_invalid_timestamps(self):
        """Should return None if timestamps cannot be parsed."""
        task = BackgroundTask(
            id="test",
            command="test",
            status=TaskStatus.COMPLETED,
            start_time="not-a-valid-timestamp",
            end_time="also-not-valid",
        )
        assert task.duration_seconds() is None
