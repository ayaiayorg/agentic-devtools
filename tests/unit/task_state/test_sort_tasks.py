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


class TestSortTasks:
    """Tests for _sort_tasks function."""

    def test_sort_unfinished_before_finished(self):
        """Test unfinished tasks come before finished tasks."""
        finished = BackgroundTask(
            id="finished",
            command="cmd",
            status=TaskStatus.COMPLETED,
            start_time="2024-01-01T00:00:00+00:00",
            end_time="2024-01-01T00:01:00+00:00",
        )
        unfinished = BackgroundTask(
            id="unfinished",
            command="cmd",
            status=TaskStatus.RUNNING,
            start_time="2024-01-01T00:02:00+00:00",
        )

        sorted_tasks = _sort_tasks([finished, unfinished])

        assert sorted_tasks[0].id == "unfinished"
        assert sorted_tasks[1].id == "finished"

    def test_sort_unfinished_by_start_time(self):
        """Test unfinished tasks sorted by start time (earliest first)."""
        task1 = BackgroundTask(
            id="later",
            command="cmd",
            status=TaskStatus.RUNNING,
            start_time="2024-01-01T00:02:00+00:00",
        )
        task2 = BackgroundTask(
            id="earlier",
            command="cmd",
            status=TaskStatus.PENDING,
            start_time="2024-01-01T00:01:00+00:00",
        )

        sorted_tasks = _sort_tasks([task1, task2])

        assert sorted_tasks[0].id == "earlier"
        assert sorted_tasks[1].id == "later"

    def test_sort_finished_by_end_time(self):
        """Test finished tasks sorted by end time (earliest first)."""
        task1 = BackgroundTask(
            id="ended-later",
            command="cmd",
            status=TaskStatus.COMPLETED,
            start_time="2024-01-01T00:00:00+00:00",
            end_time="2024-01-01T00:03:00+00:00",
        )
        task2 = BackgroundTask(
            id="ended-earlier",
            command="cmd",
            status=TaskStatus.COMPLETED,
            start_time="2024-01-01T00:00:00+00:00",
            end_time="2024-01-01T00:01:00+00:00",
        )

        sorted_tasks = _sort_tasks([task1, task2])

        assert sorted_tasks[0].id == "ended-earlier"
        assert sorted_tasks[1].id == "ended-later"

    def test_sort_tasks_with_invalid_start_time(self):
        """Test sorting handles invalid start_time gracefully."""
        task_valid = BackgroundTask(
            id="valid",
            command="cmd",
            status=TaskStatus.RUNNING,
            start_time="2024-01-01T00:01:00+00:00",
        )
        task_invalid = BackgroundTask(
            id="invalid",
            command="cmd",
            status=TaskStatus.RUNNING,
            start_time="not-a-timestamp",
        )

        # Should not raise, invalid dates get min datetime
        sorted_tasks = _sort_tasks([task_valid, task_invalid])
        assert len(sorted_tasks) == 2

    def test_sort_tasks_with_invalid_end_time(self):
        """Test sorting handles invalid end_time gracefully."""
        task_valid = BackgroundTask(
            id="valid",
            command="cmd",
            status=TaskStatus.COMPLETED,
            start_time="2024-01-01T00:01:00+00:00",
            end_time="2024-01-01T00:02:00+00:00",
        )
        task_invalid = BackgroundTask(
            id="invalid",
            command="cmd",
            status=TaskStatus.COMPLETED,
            start_time="2024-01-01T00:01:00+00:00",
            end_time="not-a-timestamp",
        )

        # Should not raise, invalid dates get max datetime
        sorted_tasks = _sort_tasks([task_valid, task_invalid])
        assert len(sorted_tasks) == 2
