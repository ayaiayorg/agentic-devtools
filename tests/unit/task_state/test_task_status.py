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


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_status_values(self):
        """Test TaskStatus enum has expected values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"

    def test_status_from_string(self):
        """Test creating TaskStatus from string value."""
        assert TaskStatus("pending") == TaskStatus.PENDING
        assert TaskStatus("running") == TaskStatus.RUNNING
        assert TaskStatus("completed") == TaskStatus.COMPLETED
        assert TaskStatus("failed") == TaskStatus.FAILED
