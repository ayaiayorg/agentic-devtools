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


class TestGetIncompleteMostRecentPerCommand:
    """Tests for get_incomplete_most_recent_per_command function."""

    def test_empty_tasks(self):
        """Test with no tasks."""
        from agentic_devtools.task_state import get_incomplete_most_recent_per_command

        with patch("agentic_devtools.task_state.get_most_recent_tasks_per_command", return_value={}):
            result = get_incomplete_most_recent_per_command()

        assert result == []

    def test_all_complete(self):
        """Test with all completed tasks."""
        from agentic_devtools.task_state import get_incomplete_most_recent_per_command

        task1 = BackgroundTask.create(command="agdt-git-save-work")
        task1.mark_completed(exit_code=0)
        task2 = BackgroundTask.create(command="agdt-add-jira-comment")
        task2.mark_failed(exit_code=1)

        with patch(
            "agentic_devtools.task_state.get_most_recent_tasks_per_command",
            return_value={"agdt-git-save-work": task1, "agdt-add-jira-comment": task2},
        ):
            result = get_incomplete_most_recent_per_command()

        # Both completed and failed are considered "complete"
        assert result == []

    def test_returns_incomplete_tasks(self):
        """Test that incomplete tasks are returned."""
        from agentic_devtools.task_state import get_incomplete_most_recent_per_command

        task1 = BackgroundTask.create(command="agdt-git-save-work")
        task1.mark_running()
        task2 = BackgroundTask.create(command="agdt-add-jira-comment")
        task2.mark_completed(exit_code=0)
        task3 = BackgroundTask.create(command="agdt-create-pr")
        # task3 is pending (default state)

        with patch(
            "agentic_devtools.task_state.get_most_recent_tasks_per_command",
            return_value={
                "agdt-git-save-work": task1,
                "agdt-add-jira-comment": task2,
                "agdt-create-pr": task3,
            },
        ):
            result = get_incomplete_most_recent_per_command()

        assert len(result) == 2
        result_ids = {t.id for t in result}
        assert task1.id in result_ids  # running
        assert task3.id in result_ids  # pending

    def test_excludes_specified_task(self):
        """Test that exclude_task_id parameter works."""
        from agentic_devtools.task_state import get_incomplete_most_recent_per_command

        task1 = BackgroundTask.create(command="agdt-git-save-work")
        task1.mark_running()
        task2 = BackgroundTask.create(command="agdt-add-jira-comment")
        task2.mark_running()

        with patch(
            "agentic_devtools.task_state.get_most_recent_tasks_per_command",
            return_value={"agdt-git-save-work": task1, "agdt-add-jira-comment": task2},
        ):
            result = get_incomplete_most_recent_per_command(exclude_task_id=task1.id)

        assert len(result) == 1
        assert result[0].id == task2.id
