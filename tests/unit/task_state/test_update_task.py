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


class TestUpdateTask:
    """Tests for update_task function."""

    def test_update_existing_task(self):
        """Test updating an existing task."""
        task = BackgroundTask.create(command="cmd")

        with patch("agentic_devtools.task_state.load_state") as mock_load, patch(
            "agentic_devtools.task_state.save_state"
        ) as mock_save, patch("agentic_devtools.task_state._update_task_in_all_tasks"), patch(
            "agentic_devtools.task_state._append_to_all_tasks"
        ):
            mock_load.return_value = {"background": {"recentTasks": [task.to_dict()]}}

            task.mark_running()
            result = update_task(task, use_locking=False)

        assert result is True
        mock_save.assert_called_once()

    def test_update_nonexistent_task(self):
        """Test updating a non-existent task returns False."""
        task = BackgroundTask.create(command="cmd")

        with patch("agentic_devtools.task_state.load_state") as mock_load:
            mock_load.return_value = {"background": {"recentTasks": []}}

            result = update_task(task, use_locking=False)

        assert result is False
