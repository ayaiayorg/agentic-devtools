"""
Tests for task_state module.
"""

from agentic_devtools.task_state import (
    TaskStatus,
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
