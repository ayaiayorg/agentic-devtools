"""
Tests for task_state module.
"""

from agentic_devtools.task_state import (
    BackgroundTask,
    TaskStatus,
)


class TestTaskLifecycle:
    """Integration tests for full task lifecycle."""

    def test_full_lifecycle_success(self):
        """Test complete lifecycle: create -> running -> completed."""
        task = BackgroundTask.create(command="agdt-test-cmd")
        assert task.status == TaskStatus.PENDING

        # Start running
        task.mark_running()
        assert task.status == TaskStatus.RUNNING

        # Complete successfully
        task.mark_completed(exit_code=0)
        assert task.status == TaskStatus.COMPLETED
        assert task.exit_code == 0
        assert task.end_time is not None

    def test_full_lifecycle_failure(self):
        """Test complete lifecycle: create -> running -> failed."""
        task = BackgroundTask.create(command="agdt-failing-cmd")

        task.mark_running()
        task.mark_failed(exit_code=1, error_message="Process crashed")

        assert task.status == TaskStatus.FAILED
        assert task.exit_code == 1
        assert task.error_message == "Process crashed"
