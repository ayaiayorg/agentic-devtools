"""
Tests for task_state module.
"""

from unittest.mock import patch

from agentic_devtools.task_state import (
    BackgroundTask,
    add_task,
    get_failed_most_recent_per_command,
)


class TestGetFailedMostRecentPerCommand:
    """Tests for get_failed_most_recent_per_command function."""

    def test_empty_tasks(self):
        """Test with no tasks."""
        from agentic_devtools.task_state import get_failed_most_recent_per_command

        with patch("agentic_devtools.task_state.get_most_recent_tasks_per_command", return_value={}):
            result = get_failed_most_recent_per_command()

        assert result == []

    def test_all_successful(self):
        """Test with all successful tasks."""
        from agentic_devtools.task_state import get_failed_most_recent_per_command

        task1 = BackgroundTask.create(command="agdt-git-save-work")
        task1.mark_completed(exit_code=0)

        with patch(
            "agentic_devtools.task_state.get_most_recent_tasks_per_command",
            return_value={"agdt-git-save-work": task1},
        ):
            result = get_failed_most_recent_per_command()

        assert result == []

    def test_returns_failed_tasks(self):
        """Test that failed tasks are returned."""
        from agentic_devtools.task_state import get_failed_most_recent_per_command

        task1 = BackgroundTask.create(command="agdt-git-save-work")
        task1.mark_failed(exit_code=1)
        task2 = BackgroundTask.create(command="agdt-add-jira-comment")
        task2.mark_completed(exit_code=0)

        with patch(
            "agentic_devtools.task_state.get_most_recent_tasks_per_command",
            return_value={"agdt-git-save-work": task1, "agdt-add-jira-comment": task2},
        ):
            result = get_failed_most_recent_per_command()

        assert len(result) == 1
        assert result[0].id == task1.id

    def test_excludes_specified_task(self):
        """Test that exclude_task_id parameter works."""
        from agentic_devtools.task_state import get_failed_most_recent_per_command

        task1 = BackgroundTask.create(command="agdt-git-save-work")
        task1.mark_failed(exit_code=1)
        task2 = BackgroundTask.create(command="agdt-add-jira-comment")
        task2.mark_failed(exit_code=1)

        with patch(
            "agentic_devtools.task_state.get_most_recent_tasks_per_command",
            return_value={"agdt-git-save-work": task1, "agdt-add-jira-comment": task2},
        ):
            result = get_failed_most_recent_per_command(exclude_task_id=task1.id)

        assert len(result) == 1
        assert result[0].id == task2.id

    def test_exclude_commands_skips_matching_command(self, tmp_path):
        """Test that exclude_commands parameter skips tasks with matching commands.

        This is the bug fix scenario: when a task for dfly-git-save-work succeeds,
        we should not report an older failed dfly-git-save-work task.
        """
        import time

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            # Create an older failed task for dfly-git-save-work
            older_failed = BackgroundTask.create(command="agdt-git-save-work")
            older_failed.mark_running()
            older_failed.mark_failed(exit_code=1)
            add_task(older_failed)

            # Small delay to ensure different timestamps
            time.sleep(0.01)

            # Create a newer successful task for dfly-git-save-work
            newer_success = BackgroundTask.create(command="agdt-git-save-work")
            newer_success.mark_running()
            newer_success.mark_completed(exit_code=0)
            add_task(newer_success)

            # Create a failed task for a different command
            other_failed = BackgroundTask.create(command="agdt-other-cmd")
            other_failed.mark_running()
            other_failed.mark_failed(exit_code=1)
            add_task(other_failed)

            # When excluding the dfly-git-save-work command, we should not see the older failed task
            result = get_failed_most_recent_per_command(
                exclude_task_id=newer_success.id,
                exclude_commands=["agdt-git-save-work"],
            )

            # Should only see the other_failed task, not older_failed
            assert len(result) == 1
            assert result[0].command == "agdt-other-cmd"

    def test_exclude_commands_empty_list(self, tmp_path):
        """Test that empty exclude_commands list has no effect."""
        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            failed_task = BackgroundTask.create(command="agdt-cmd-a")
            failed_task.mark_running()
            failed_task.mark_failed(exit_code=1)
            add_task(failed_task)

            result = get_failed_most_recent_per_command(exclude_commands=[])
            assert len(result) == 1
            assert result[0].command == "agdt-cmd-a"

    def test_exclude_commands_none(self, tmp_path):
        """Test that None exclude_commands has no effect."""
        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            failed_task = BackgroundTask.create(command="agdt-cmd-a")
            failed_task.mark_running()
            failed_task.mark_failed(exit_code=1)
            add_task(failed_task)

            result = get_failed_most_recent_per_command(exclude_commands=None)
            assert len(result) == 1
            assert result[0].command == "agdt-cmd-a"

    def test_exclude_commands_multiple(self, tmp_path):
        """Test excluding multiple commands."""
        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            # Create failed tasks for different commands
            failed_a = BackgroundTask.create(command="agdt-cmd-a")
            failed_a.mark_running()
            failed_a.mark_failed(exit_code=1)
            add_task(failed_a)

            failed_b = BackgroundTask.create(command="agdt-cmd-b")
            failed_b.mark_running()
            failed_b.mark_failed(exit_code=1)
            add_task(failed_b)

            failed_c = BackgroundTask.create(command="agdt-cmd-c")
            failed_c.mark_running()
            failed_c.mark_failed(exit_code=1)
            add_task(failed_c)

            result = get_failed_most_recent_per_command(exclude_commands=["agdt-cmd-a", "agdt-cmd-b"])
            assert len(result) == 1
            assert result[0].command == "agdt-cmd-c"
