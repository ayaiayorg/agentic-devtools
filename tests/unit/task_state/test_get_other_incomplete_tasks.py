"""
Tests for task_state module.
"""

from unittest.mock import patch

from agentic_devtools.task_state import (
    BackgroundTask,
    add_task,
)


class TestGetOtherIncompleteTasks:
    """Tests for get_other_incomplete_tasks function."""

    def test_returns_empty_when_no_tasks(self, tmp_path):
        """Test returns empty list when no tasks exist."""
        from agentic_devtools.task_state import get_other_incomplete_tasks

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            result = get_other_incomplete_tasks("some-task-id")
            assert result == []

    def test_excludes_current_task_id(self, tmp_path):
        """Test excludes the specified task ID from results."""
        from agentic_devtools.task_state import get_other_incomplete_tasks

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            task1 = BackgroundTask.create(command="cmd1")
            task1.mark_running()
            add_task(task1)

            task2 = BackgroundTask.create(command="cmd2")
            task2.mark_running()
            add_task(task2)

            # Get incomplete tasks excluding task1
            result = get_other_incomplete_tasks(task1.id)

            assert len(result) == 1
            assert result[0].id == task2.id

    def test_excludes_completed_tasks(self, tmp_path):
        """Test excludes completed tasks from results."""
        from agentic_devtools.task_state import get_other_incomplete_tasks

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            running_task = BackgroundTask.create(command="running")
            running_task.mark_running()
            add_task(running_task)

            completed_task = BackgroundTask.create(command="completed")
            completed_task.mark_running()
            completed_task.mark_completed(exit_code=0)
            add_task(completed_task)

            # Get incomplete tasks excluding a fake ID
            result = get_other_incomplete_tasks("fake-id")

            assert len(result) == 1
            assert result[0].id == running_task.id

    def test_excludes_failed_tasks(self, tmp_path):
        """Test excludes failed tasks from results."""
        from agentic_devtools.task_state import get_other_incomplete_tasks

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            running_task = BackgroundTask.create(command="running")
            running_task.mark_running()
            add_task(running_task)

            failed_task = BackgroundTask.create(command="failed")
            failed_task.mark_running()
            failed_task.mark_failed(exit_code=1, error_message="Error")
            add_task(failed_task)

            result = get_other_incomplete_tasks("fake-id")

            assert len(result) == 1
            assert result[0].id == running_task.id
