"""Tests for get_recent_tasks function."""

from unittest.mock import patch

from agentic_devtools.task_state import BackgroundTask, TaskStatus, get_recent_tasks


class TestGetRecentTasks:
    """Tests for get_recent_tasks function."""

    def test_returns_empty_list_when_no_tasks(self):
        """Should return empty list when state has no background tasks."""
        with patch("agentic_devtools.task_state.load_state") as mock_load:
            mock_load.return_value = {}

            result = get_recent_tasks(use_locking=False)

        assert result == []

    def test_returns_tasks_from_state(self):
        """Should return tasks from background.recentTasks in state."""
        task = BackgroundTask.create(command="agdt-test")

        with patch("agentic_devtools.task_state.load_state") as mock_load:
            mock_load.return_value = {
                "background": {"recentTasks": [task.to_dict()]}
            }

            result = get_recent_tasks(use_locking=False)

        assert len(result) == 1
        assert result[0].id == task.id
        assert result[0].command == "agdt-test"

    def test_returns_multiple_tasks(self):
        """Should return all tasks from state."""
        task1 = BackgroundTask.create(command="agdt-test")
        task2 = BackgroundTask.create(command="agdt-test-quick")

        with patch("agentic_devtools.task_state.load_state") as mock_load:
            mock_load.return_value = {
                "background": {"recentTasks": [task1.to_dict(), task2.to_dict()]}
            }

            result = get_recent_tasks(use_locking=False)

        assert len(result) == 2
        ids = {t.id for t in result}
        assert task1.id in ids
        assert task2.id in ids

    def test_returns_tasks_sorted_unfinished_first(self):
        """Unfinished tasks should appear before finished tasks."""
        finished = BackgroundTask.create(command="agdt-test")
        finished.mark_completed(exit_code=0)

        pending = BackgroundTask.create(command="agdt-test-quick")

        with patch("agentic_devtools.task_state.load_state") as mock_load:
            mock_load.return_value = {
                "background": {
                    "recentTasks": [finished.to_dict(), pending.to_dict()]
                }
            }

            result = get_recent_tasks(use_locking=False)

        # Pending task (no end_time) should come first
        unfinished = [t for t in result if t.status == TaskStatus.PENDING]
        assert len(unfinished) == 1
        assert result[0].id == unfinished[0].id
