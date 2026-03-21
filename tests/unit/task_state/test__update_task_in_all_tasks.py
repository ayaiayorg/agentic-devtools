"""Tests for _update_task_in_all_tasks function."""

from unittest.mock import patch

from agentic_devtools.task_state import (
    BackgroundTask,
    _update_task_in_all_tasks,
    add_task,
    get_all_tasks,
)


class TestUpdateTaskInAllTasks:
    """Tests for _update_task_in_all_tasks function."""

    def test_updates_existing_task(self, tmp_path):
        """Update a task that already exists in the all-tasks file."""
        with patch("agentic_devtools.task_state.get_state_dir", return_value=tmp_path), patch(
            "agentic_devtools.state.get_state_dir", return_value=tmp_path
        ):
            task = BackgroundTask.create(command="agdt-test-cmd")
            add_task(task, use_locking=False)

            # Mark the task as running and update it
            task.mark_running()
            _update_task_in_all_tasks(task)

            # Verify update persisted
            all_tasks = get_all_tasks()
            found = [t for t in all_tasks if t.id == task.id]
            assert len(found) == 1
            assert found[0].status.value == "running"
