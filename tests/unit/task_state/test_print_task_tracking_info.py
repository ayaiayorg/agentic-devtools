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


class TestPrintTaskTrackingInfo:
    """Tests for print_task_tracking_info function."""

    def test_sets_task_id_in_state(self, tmp_path, capsys):
        """Test that task_id is automatically set in state."""
        from agentic_devtools.state import get_value
        from agentic_devtools.task_state import print_task_tracking_info

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            task = BackgroundTask.create(command="agdt-test-cmd")
            print_task_tracking_info(task, "Testing task")

            assert get_value("background.task_id") == task.id

    def test_prints_task_started_message(self, tmp_path, capsys):
        """Test that task started message is printed."""
        from agentic_devtools.task_state import print_task_tracking_info

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            task = BackgroundTask.create(command="agdt-test-cmd")
            print_task_tracking_info(task, "Testing task")

            captured = capsys.readouterr()
            assert "Background task started" in captured.out
            assert "agdt-test-cmd" in captured.out
            assert task.id in captured.out
            assert "task_id automatically set" in captured.out

    def test_prints_action_description(self, tmp_path, capsys):
        """Test that action description is printed."""
        from agentic_devtools.task_state import print_task_tracking_info

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            task = BackgroundTask.create(command="agdt-test-cmd")
            print_task_tracking_info(task, "Adding comment to DFLY-1234")

            captured = capsys.readouterr()
            assert "Adding comment to DFLY-1234..." in captured.out

    def test_prints_tracking_commands(self, tmp_path, capsys):
        """Test that tracking commands are printed."""
        from agentic_devtools.task_state import print_task_tracking_info

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            task = BackgroundTask.create(command="agdt-test-cmd")
            print_task_tracking_info(task, "Testing")

            captured = capsys.readouterr()
            # Simplified output now just shows dfly-task-wait
            assert "agdt-task-wait" in captured.out
            # Should NOT show the verbose commands anymore
            assert '--id "<task-id>"' not in captured.out

    def test_shows_other_incomplete_tasks(self, tmp_path, capsys):
        """Test that simplified output does NOT show other incomplete tasks (moved to task_wait)."""
        from agentic_devtools.task_state import print_task_tracking_info

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            # Add a running task first
            other_task = BackgroundTask.create(command="agdt-other-cmd")
            other_task.mark_running()
            add_task(other_task)

            # Now print info for a new task
            new_task = BackgroundTask.create(command="agdt-new-cmd")
            print_task_tracking_info(new_task, "Testing")

            captured = capsys.readouterr()
            # Other tasks are now NOT shown in print_task_tracking_info
            # They are handled by task_wait instead
            assert "Other recent incomplete background tasks:" not in captured.out
            # Just shows simple dfly-task-wait instruction
            assert "agdt-task-wait" in captured.out
