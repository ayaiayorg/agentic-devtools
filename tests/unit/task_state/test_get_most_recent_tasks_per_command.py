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


class TestGetMostRecentTasksPerCommand:
    """Tests for get_most_recent_tasks_per_command function."""

    def test_empty_tasks(self):
        """Test with no tasks."""

        with patch("agentic_devtools.task_state.get_recent_tasks", return_value=[]):
            result = get_most_recent_tasks_per_command()

        assert result == {}

    def test_single_task_per_command(self):
        """Test with one task per command."""

        task1 = BackgroundTask.create(command="agdt-git-save-work")
        task2 = BackgroundTask.create(command="agdt-add-jira-comment")

        with patch("agentic_devtools.task_state.get_recent_tasks", return_value=[task1, task2]):
            result = get_most_recent_tasks_per_command()

        assert len(result) == 2
        assert result["agdt-git-save-work"].id == task1.id
        assert result["agdt-add-jira-comment"].id == task2.id

    def test_multiple_tasks_same_command_returns_most_recent(self):
        """Test that most recent task is returned when multiple exist for same command."""

        # Create tasks with different start times
        task1 = BackgroundTask.create(command="agdt-git-save-work")
        task2 = BackgroundTask.create(command="agdt-git-save-work")  # More recent

        # List is already sorted with most recent first (task2 first)
        with patch("agentic_devtools.task_state.get_recent_tasks", return_value=[task2, task1]):
            result = get_most_recent_tasks_per_command()

        assert len(result) == 1
        # task2 should be selected as it appears first (most recent)
        assert result["agdt-git-save-work"].id == task2.id
