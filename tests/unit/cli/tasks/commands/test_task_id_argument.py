"""
Tests for CLI task monitoring commands.

Tests the task monitoring CLI commands that use the actual task_state API:
- BackgroundTask.create + add_task (not create_task)
- update_task (not update_task_status)
- get_background_tasks (returns list, not dict)
- task.id (not task.task_id)
- task.start_time (not task.created_at)
"""

import sys
from unittest.mock import patch

import pytest

from agentic_devtools.cli.tasks.commands import (
    task_log,
    task_status,
    task_wait,
)
from agentic_devtools.task_state import (
    BackgroundTask,
    add_task,
    update_task,
)


@pytest.fixture
def mock_state_dir(tmp_path):
    """Fixture to mock the state directory."""
    # Patch get_state_dir in the state module (where it's defined)
    with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
        yield tmp_path


def _create_and_add_task(command: str) -> BackgroundTask:
    """Helper to create and add a task using the real API."""
    task = BackgroundTask.create(command=command)
    add_task(task)
    return task


class TestTaskIdArgument:
    """Tests for --id argument on task commands."""

    def test_task_status_with_id_argument(self, mock_state_dir, capsys):
        """Test task_status with --id argument."""
        task = _create_and_add_task("agdt-test-cmd")
        task.mark_running()
        update_task(task)

        # Use --id argument instead of state
        task_status(_argv=["--id", task.id])

        captured = capsys.readouterr()
        assert task.id in captured.out
        assert "agdt-test-cmd" in captured.out
        assert "running" in captured.out.lower()

    def test_task_status_id_updates_state(self, mock_state_dir, capsys):
        """Test --id argument updates background.task_id in state."""
        from agentic_devtools.state import get_value

        task = _create_and_add_task("agdt-test-cmd")
        task.mark_running()
        update_task(task)

        task_status(_argv=["--id", task.id])

        # Verify state was updated
        assert get_value("background.task_id") == task.id

    def test_task_log_with_id_argument(self, mock_state_dir, capsys, tmp_path):
        """Test task_log with --id argument."""
        # Create task with log file
        log_file = tmp_path / "test.log"
        log_file.write_text("Test log content\n")

        task = BackgroundTask.create(command="agdt-test-cmd", log_file=log_file)
        add_task(task)

        task_log(_argv=["--id", task.id])

        captured = capsys.readouterr()
        assert "Test log content" in captured.out

    def test_task_wait_with_id_argument(self, mock_state_dir, capsys):
        """Test task_wait with --id argument for completed task."""
        task = _create_and_add_task("agdt-test-cmd")
        task.mark_running()
        task.mark_completed(exit_code=0)
        update_task(task)

        # Should not block since task is already completed
        # Now returns normally when task completes and all tasks are done
        task_wait(_argv=["--id", task.id])

        captured = capsys.readouterr()
        assert "completed" in captured.out.lower()

    def test_task_wait_ignores_older_failed_same_command(self, mock_state_dir, capsys):
        """Test task_wait doesn't report older failed tasks for the same command.

        Bug fix: When a task for agdt-git-save-work succeeds, we should NOT report
        an older failed agdt-git-save-work task as needing attention.
        """
        import time

        # Create an older failed task for agdt-git-save-work
        older_failed = _create_and_add_task("agdt-git-save-work")
        older_failed.mark_running()
        older_failed.mark_failed(exit_code=1)
        update_task(older_failed)

        # Small delay to ensure different timestamps
        time.sleep(0.01)

        # Create a newer successful task for agdt-git-save-work
        newer_success = _create_and_add_task("agdt-git-save-work")
        newer_success.mark_running()
        newer_success.mark_completed(exit_code=0)
        update_task(newer_success)

        with patch(
            "agentic_devtools.state.load_state",
            return_value={"background": {"task_id": newer_success.id}},
        ):
            # Should complete normally - no failed tasks should be reported
            task_wait(_argv=["--id", newer_success.id])

        captured = capsys.readouterr()
        # Should show "ALL TASKS COMPLETED" not "OTHER TASKS FAILED"
        assert "all tasks completed" in captured.out.lower()
        assert "other tasks failed" not in captured.out.lower()

    def test_task_wait_still_reports_failed_different_command(self, mock_state_dir, capsys):
        """Test task_wait still reports failed tasks for different commands.

        When a task succeeds, we should still report failed tasks for OTHER commands.
        """
        # Create a failed task for a different command
        failed_other = _create_and_add_task("agdt-other-cmd")
        failed_other.mark_running()
        failed_other.mark_failed(exit_code=1)
        update_task(failed_other)

        # Create a successful task for agdt-git-save-work
        success_task = _create_and_add_task("agdt-git-save-work")
        success_task.mark_running()
        success_task.mark_completed(exit_code=0)
        update_task(success_task)

        # Use --id argument which sets task_id in state directly
        # Don't patch load_state - we need the real state with the tasks
        with pytest.raises(SystemExit) as exc_info:
            task_wait(_argv=["--id", success_task.id])

        # Should exit 0 (task succeeded, but reporting other failures)
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        # Should show the other failed task
        assert "other tasks failed" in captured.out.lower() or "agdt-other-cmd" in captured.out

    def test_task_wait_picks_up_id_from_sys_argv(self, mock_state_dir, capsys, monkeypatch):
        """Test task_wait reads --id from sys.argv when _argv is not provided (real CLI behavior).

        This is the bug fix test: previously _parse_wait_args used `_argv or []`
        which silently dropped sys.argv when _argv was None. Now it uses
        parse_known_args(_argv) which falls back to sys.argv[1:] when _argv is None.
        """
        task = _create_and_add_task("agdt-test-cmd")
        task.mark_running()
        task.mark_completed(exit_code=0)
        update_task(task)

        # Simulate the real CLI invocation: agdt-task-wait --id <task-id>
        monkeypatch.setattr(sys, "argv", ["agdt-task-wait", "--id", task.id])

        # Call without _argv (as the CLI entry point does)
        task_wait()

        captured = capsys.readouterr()
        assert "completed" in captured.out.lower()
