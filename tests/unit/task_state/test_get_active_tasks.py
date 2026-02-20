"""
Tests for task_state module.
"""

from unittest.mock import patch

from agentic_devtools.task_state import (
    BackgroundTask,
    get_active_tasks,
)


class TestGetActiveTasks:
    """Tests for get_active_tasks function."""

    def test_get_active_tasks(self):
        """Test getting active (pending/running) tasks."""
        task1 = BackgroundTask.create(command="cmd1")  # pending
        task2 = BackgroundTask.create(command="cmd2")
        task2.mark_running()
        task3 = BackgroundTask.create(command="cmd3")
        task3.mark_completed()

        with patch("agentic_devtools.task_state.load_state") as mock_load:
            mock_load.return_value = {"background": {"recentTasks": [t.to_dict() for t in [task1, task2, task3]]}}

            active = get_active_tasks(use_locking=False)

        assert len(active) == 2
        active_ids = {t.id for t in active}
        assert task1.id in active_ids
        assert task2.id in active_ids
        assert task3.id not in active_ids
