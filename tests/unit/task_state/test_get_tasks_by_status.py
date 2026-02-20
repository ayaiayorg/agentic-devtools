"""
Tests for task_state module.
"""

from unittest.mock import patch

from agentic_devtools.task_state import (
    BackgroundTask,
    TaskStatus,
    get_tasks_by_status,
)


class TestGetTasksByStatus:
    """Tests for get_tasks_by_status function."""

    def test_filter_by_status(self):
        """Test filtering tasks by status."""
        task1 = BackgroundTask.create(command="cmd1")
        task2 = BackgroundTask.create(command="cmd2")
        task2.mark_running()
        task3 = BackgroundTask.create(command="cmd3")
        task3.mark_completed()

        with patch("agentic_devtools.task_state.load_state") as mock_load:
            mock_load.return_value = {"background": {"recentTasks": [t.to_dict() for t in [task1, task2, task3]]}}

            pending = get_tasks_by_status(TaskStatus.PENDING, use_locking=False)
            running = get_tasks_by_status(TaskStatus.RUNNING, use_locking=False)
            completed = get_tasks_by_status(TaskStatus.COMPLETED, use_locking=False)

        assert len(pending) == 1
        assert pending[0].id == task1.id
        assert len(running) == 1
        assert running[0].id == task2.id
        assert len(completed) == 1
        assert completed[0].id == task3.id
