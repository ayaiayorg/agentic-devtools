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


class TestGetBackgroundTasks:
    """Tests for get_background_tasks function."""

    def test_get_all_tasks_empty(self):
        """Test get_background_tasks with no tasks."""
        with patch("agentic_devtools.task_state.load_state") as mock_load:
            mock_load.return_value = {}

            tasks = get_background_tasks(use_locking=False)

        assert tasks == []

    def test_get_all_tasks_multiple(self):
        """Test get_background_tasks returns all tasks."""
        task1 = BackgroundTask.create(command="cmd1")
        task2 = BackgroundTask.create(command="cmd2")
        task3 = BackgroundTask.create(command="cmd3")

        with patch("agentic_devtools.task_state.load_state") as mock_load:
            mock_load.return_value = {"background": {"recentTasks": [t.to_dict() for t in [task1, task2, task3]]}}

            all_tasks = get_background_tasks(use_locking=False)

        assert len(all_tasks) == 3
        task_ids = {t.id for t in all_tasks}
        assert task1.id in task_ids
        assert task2.id in task_ids
        assert task3.id in task_ids
