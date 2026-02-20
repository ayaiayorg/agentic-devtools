"""
Tests for task_state module.
"""

from unittest.mock import patch

from agentic_devtools.task_state import (
    BackgroundTask,
    remove_task,
)


class TestRemoveTask:
    """Tests for remove_task function."""

    def test_remove_existing_task(self):
        """Test removing an existing task."""
        task = BackgroundTask.create(command="cmd")

        with patch("agentic_devtools.task_state.load_state") as mock_load, patch(
            "agentic_devtools.task_state.save_state"
        ) as mock_save, patch("agentic_devtools.task_state._load_all_tasks_file", return_value=[]), patch(
            "agentic_devtools.task_state._save_all_tasks_file"
        ):
            mock_load.return_value = {"background": {"recentTasks": [task.to_dict()]}}

            result = remove_task(task.id, use_locking=False)

        assert result is True
        mock_save.assert_called_once()
        saved_state = mock_save.call_args[0][0]
        assert len(saved_state["background"]["recentTasks"]) == 0

    def test_remove_nonexistent_task(self):
        """Test removing a non-existent task returns False."""
        with patch("agentic_devtools.task_state.load_state") as mock_load, patch(
            "agentic_devtools.task_state._load_all_tasks_file", return_value=[]
        ), patch("agentic_devtools.task_state._save_all_tasks_file"):
            mock_load.return_value = {"background": {"recentTasks": []}}

            result = remove_task("nonexistent-id", use_locking=False)

        assert result is False

    def test_remove_preserves_other_tasks(self):
        """Test removing one task preserves others."""
        task1 = BackgroundTask.create(command="cmd1")
        task2 = BackgroundTask.create(command="cmd2")

        with patch("agentic_devtools.task_state.load_state") as mock_load, patch(
            "agentic_devtools.task_state.save_state"
        ) as mock_save, patch("agentic_devtools.task_state._load_all_tasks_file", return_value=[]), patch(
            "agentic_devtools.task_state._save_all_tasks_file"
        ):
            mock_load.return_value = {"background": {"recentTasks": [task1.to_dict(), task2.to_dict()]}}

            remove_task(task1.id, use_locking=False)

        saved_state = mock_save.call_args[0][0]
        assert len(saved_state["background"]["recentTasks"]) == 1
        assert saved_state["background"]["recentTasks"][0]["id"] == task2.id
