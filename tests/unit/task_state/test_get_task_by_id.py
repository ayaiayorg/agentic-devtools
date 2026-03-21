"""
Tests for task_state module.
"""

from unittest.mock import patch

from agentic_devtools.task_state import (
    BackgroundTask,
    TaskStatus,
    get_task_by_id,
)


class TestGetTaskById:
    """Tests for get_task_by_id function."""

    def test_get_existing_task(self):
        """Test retrieving an existing task."""
        task = BackgroundTask.create(command="agdt-cmd")

        with patch("agentic_devtools.task_state.load_state") as mock_load, patch(
            "agentic_devtools.task_state.get_task_from_all_tasks", return_value=None
        ):
            mock_load.return_value = {"background": {"recentTasks": [task.to_dict()]}}

            retrieved = get_task_by_id(task.id, use_locking=False)

        assert retrieved is not None
        assert retrieved.id == task.id
        assert retrieved.command == task.command

    def test_get_nonexistent_task(self):
        """Test retrieving a non-existent task returns None."""
        with patch("agentic_devtools.task_state.load_state") as mock_load, patch(
            "agentic_devtools.task_state.get_task_from_all_tasks", return_value=None
        ):
            mock_load.return_value = {"background": {"recentTasks": []}}

            result = get_task_by_id("nonexistent-task-id", use_locking=False)

        assert result is None

    def test_get_task_partial_id_match(self):
        """Test retrieving task with partial ID match."""
        task = BackgroundTask(
            id="12345678-1234-1234-1234-123456789abc",
            command="agdt-cmd",
            status=TaskStatus.PENDING,
            start_time="2024-01-01T00:00:00+00:00",
        )

        with patch("agentic_devtools.task_state.load_state") as mock_load, patch(
            "agentic_devtools.task_state.get_task_from_all_tasks", return_value=None
        ):
            mock_load.return_value = {"background": {"recentTasks": [task.to_dict()]}}

            # Should find by first 8 characters
            retrieved = get_task_by_id("12345678", use_locking=False)

        assert retrieved is not None
        assert retrieved.id == task.id
