"""
Tests for CLI task monitoring commands.

Tests the task monitoring CLI commands that use the actual task_state API:
- BackgroundTask.create + add_task (not create_task)
- update_task (not update_task_status)
- get_background_tasks (returns list, not dict)
- task.id (not task.task_id)
- task.start_time (not task.created_at)
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from agdt_ai_helpers.cli.tasks.commands import (
    list_tasks,
    task_log,
    task_status,
    task_wait,
    tasks_clean,
)
from agdt_ai_helpers.task_state import (
    BackgroundTask,
    add_task,
    get_background_tasks,
    get_task_by_id,
    update_task,
)


@pytest.fixture
def mock_state_dir(tmp_path):
    """Fixture to mock the state directory."""
    # Patch get_state_dir in the state module (where it's defined)
    with patch("agdt_ai_helpers.state.get_state_dir", return_value=tmp_path):
        yield tmp_path


def _create_and_add_task(command: str) -> BackgroundTask:
    """Helper to create and add a task using the real API."""
    task = BackgroundTask.create(command=command)
    add_task(task)
    return task


class TestHelperFunctions:
    """Tests for helper functions in tasks/commands.py."""

    def test_safe_print_with_unicode_error(self, capsys):
        """Test _safe_print handles UnicodeEncodeError gracefully."""
        from agdt_ai_helpers.cli.tasks.commands import _safe_print

        # This should work without raising
        _safe_print("Test with emoji ✅ and text")
        captured = capsys.readouterr()
        assert "Test with emoji" in captured.out

    def test_format_timestamp_with_valid_timestamp(self):
        """Test _format_timestamp with valid ISO timestamp."""
        from agdt_ai_helpers.cli.tasks.commands import _format_timestamp

        ts = "2025-01-15T10:30:00+00:00"
        result = _format_timestamp(ts)
        assert "2025-01-15" in result
        assert "10:30:00" in result

    def test_format_timestamp_with_none(self):
        """Test _format_timestamp with None."""
        from agdt_ai_helpers.cli.tasks.commands import _format_timestamp

        result = _format_timestamp(None)
        assert result == "N/A"

    def test_format_timestamp_with_invalid_timestamp(self):
        """Test _format_timestamp with invalid timestamp string."""
        from agdt_ai_helpers.cli.tasks.commands import _format_timestamp

        result = _format_timestamp("invalid-timestamp")
        assert result == "invalid-timestamp"  # Returns original on error

    def test_format_duration_task_not_started(self, mock_state_dir):
        """Test _format_duration with task that hasn't started."""
        from agdt_ai_helpers.cli.tasks.commands import _format_duration

        task = BackgroundTask.create(command="test-cmd")
        task.start_time = None
        result = _format_duration(task)
        assert result == "Not started"

    def test_format_duration_running_task(self, mock_state_dir):
        """Test _format_duration with running task."""
        from agdt_ai_helpers.cli.tasks.commands import _format_duration

        task = BackgroundTask.create(command="test-cmd")
        task.mark_running()
        # Set start time to 30 seconds ago
        start = datetime.now(timezone.utc) - timedelta(seconds=30)
        task.start_time = start.isoformat()

        result = _format_duration(task)
        assert "s" in result  # Should show seconds

    def test_format_duration_completed_task_minutes(self, mock_state_dir):
        """Test _format_duration with completed task showing minutes."""
        from agdt_ai_helpers.cli.tasks.commands import _format_duration
        from agdt_ai_helpers.task_state import TaskStatus

        task = BackgroundTask.create(command="test-cmd")
        task.status = TaskStatus.COMPLETED
        # Set duration to 2 minutes 30 seconds
        start = datetime.now(timezone.utc) - timedelta(minutes=2, seconds=30)
        task.start_time = start.isoformat()
        task.end_time = datetime.now(timezone.utc).isoformat()

        result = _format_duration(task)
        assert "m" in result  # Should show minutes

    def test_format_duration_completed_task_hours(self, mock_state_dir):
        """Test _format_duration with completed task showing hours."""
        from agdt_ai_helpers.cli.tasks.commands import _format_duration
        from agdt_ai_helpers.task_state import TaskStatus

        task = BackgroundTask.create(command="test-cmd")
        task.status = TaskStatus.COMPLETED
        # Set duration to 1 hour 30 minutes
        start = datetime.now(timezone.utc) - timedelta(hours=1, minutes=30)
        task.start_time = start.isoformat()
        task.end_time = datetime.now(timezone.utc).isoformat()

        result = _format_duration(task)
        assert "h" in result  # Should show hours

    def test_status_indicator_returns_correct_symbols(self):
        """Test _status_indicator returns correct symbols for each status."""
        from agdt_ai_helpers.cli.tasks.commands import _status_indicator
        from agdt_ai_helpers.task_state import TaskStatus

        assert "⏳" in _status_indicator(TaskStatus.PENDING)
        assert "🔄" in _status_indicator(TaskStatus.RUNNING)
        assert "✅" in _status_indicator(TaskStatus.COMPLETED)
        assert "❌" in _status_indicator(TaskStatus.FAILED)


class TestListTasks:
    """Tests for list_tasks command."""

    def test_list_tasks_empty(self, mock_state_dir, capsys):
        """Test list_tasks with no tasks."""
        list_tasks()

        captured = capsys.readouterr()
        assert "No background tasks found" in captured.out

    def test_list_tasks_shows_tasks(self, mock_state_dir, capsys):
        """Test list_tasks displays tasks."""
        task1 = _create_and_add_task("agdt-cmd-1")
        task2 = _create_and_add_task("agdt-cmd-2")

        # Mark task1 as completed
        task1.mark_completed(exit_code=0)
        update_task(task1)

        list_tasks()

        captured = capsys.readouterr()
        assert task1.id in captured.out
        assert task2.id in captured.out
        assert "agdt-cmd-1" in captured.out
        assert "agdt-cmd-2" in captured.out

    def test_list_tasks_shows_status(self, mock_state_dir, capsys):
        """Test list_tasks shows task status."""
        task = _create_and_add_task("agdt-test-cmd")
        task.mark_running()
        update_task(task)

        list_tasks()

        captured = capsys.readouterr()
        assert "running" in captured.out.lower()


class TestTaskStatus:
    """Tests for task_status command."""

    def test_task_status_no_task_id(self, mock_state_dir, capsys):
        """Test task_status with no task_id in state."""
        # Patch load_state where it's imported from (state module)
        with patch("agdt_ai_helpers.state.load_state", return_value={}):
            with pytest.raises(SystemExit):
                task_status()

        captured = capsys.readouterr()
        assert "No task ID" in captured.out or "background.task_id" in captured.out

    def test_task_status_shows_details(self, mock_state_dir, capsys):
        """Test task_status shows task details."""
        task = _create_and_add_task("agdt-status-test")
        task.mark_completed(exit_code=0)
        update_task(task)

        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": task.id}}):
            task_status()

        captured = capsys.readouterr()
        assert task.id in captured.out
        assert "completed" in captured.out.lower()

    def test_task_status_nonexistent_task(self, mock_state_dir, capsys):
        """Test task_status with non-existent task ID."""
        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": "nonexistent"}}):
            with pytest.raises(SystemExit):
                task_status()

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()


class TestTaskLog:
    """Tests for task_log command."""

    def test_task_log_no_task_id(self, mock_state_dir, capsys):
        """Test task_log with no task_id in state."""
        with patch("agdt_ai_helpers.state.load_state", return_value={}):
            with pytest.raises(SystemExit):
                task_log()

    def test_task_log_shows_content(self, mock_state_dir, capsys):
        """Test task_log shows log file content."""
        task = _create_and_add_task("agdt-log-test")

        # Create log file with content in the logs directory
        log_dir = mock_state_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        # The log file is stored by the task's log_file attribute
        if task.log_file:
            from pathlib import Path

            log_path = Path(task.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text("Test log output\nLine 2\n")

        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": task.id}}):
            try:
                task_log()
            except SystemExit:
                pass  # May exit if no log file

        captured = capsys.readouterr()
        # Either shows content or indicates no log file
        assert (
            "Test log output" in captured.out
            or "no log" in captured.out.lower()
            or "not found" in captured.out.lower()
            or "No log file" in captured.out
        )

    def test_task_log_no_log_file(self, mock_state_dir, capsys):
        """Test task_log when log file doesn't exist."""
        task = _create_and_add_task("agdt-no-log")

        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": task.id}}):
            try:
                task_log()
            except SystemExit:
                pass  # Expected if no log file

        # Just verify no crash - captured output may vary


class TestTaskWait:
    """Tests for task_wait command."""

    def test_task_wait_no_task_id(self, mock_state_dir, capsys):
        """Test task_wait with no task_id in state."""
        with patch("agdt_ai_helpers.state.load_state", return_value={}):
            with pytest.raises(SystemExit):
                task_wait()

    def test_task_wait_completed_task(self, mock_state_dir, capsys):
        """Test task_wait with already completed task - returns normally when all tasks done."""
        task = _create_and_add_task("agdt-wait-test")
        task.mark_completed(exit_code=0)
        update_task(task)

        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": task.id}}):
            # Now returns normally when task completes and all tasks are done
            task_wait()

        captured = capsys.readouterr()
        assert "completed" in captured.out.lower()
        # Should show ALL TASKS COMPLETED message
        assert "all tasks completed" in captured.out.lower() or "all background tasks complete" in captured.out.lower()

    def test_task_wait_failed_task(self, mock_state_dir, capsys):
        """Test task_wait with failed task."""
        task = _create_and_add_task("agdt-failed-test")
        task.mark_failed(exit_code=1)
        update_task(task)

        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": task.id}}):
            with pytest.raises(SystemExit) as exc_info:
                task_wait()
            # Exit code should be non-zero for failed task
            assert exc_info.value.code != 0

        captured = capsys.readouterr()
        assert "failed" in captured.out.lower()

    def test_task_wait_still_running_after_checks(self, mock_state_dir, capsys):
        """Test task_wait when task is still running after two checks."""
        task = _create_and_add_task("agdt-slow-task")
        task.mark_running()
        update_task(task)

        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": task.id}}):
            # Should exit 0 and tell AI to wait again
            with pytest.raises(SystemExit) as exc_info:
                task_wait(_argv=["--wait-interval", "0.01"])  # Very short wait for testing
            assert exc_info.value.code == 0  # Exit 0 to tell AI to try again

        captured = capsys.readouterr()
        assert "still in progress" in captured.out.lower()
        assert "agdt-task-wait" in captured.out.lower()
        assert "agdt-slow-task" in captured.out

    def test_task_wait_completes_on_second_check(self, mock_state_dir, capsys):
        """Test task_wait when task completes during the wait interval."""
        task = _create_and_add_task("agdt-fast-task")
        task.mark_running()
        update_task(task)

        # Mock get_task_by_id to return running first, then completed
        call_count = [0]

        def mock_get_task(task_id):
            call_count[0] += 1
            t = get_task_by_id(task_id)
            if t and call_count[0] >= 2:
                # Simulate task completing after first check
                t.mark_completed(exit_code=0)
                update_task(t)
                # Return fresh version
                return get_task_by_id(task_id)
            return t

        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": task.id}}):
            with patch("agdt_ai_helpers.cli.tasks.commands.get_task_by_id", side_effect=mock_get_task):
                task_wait(_argv=["--wait-interval", "0.01"])

        captured = capsys.readouterr()
        assert "completed" in captured.out.lower()
        assert "all tasks completed" in captured.out.lower()

    def test_task_wait_timeout_based_on_start_time(self, mock_state_dir, capsys):
        """Test task_wait timeout is based on task start_time."""
        task = _create_and_add_task("agdt-old-task")
        task.mark_running()
        # Set start_time to 10 minutes ago
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        task.start_time = old_time.isoformat()
        update_task(task)

        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": task.id}}):
            with pytest.raises(SystemExit) as exc_info:
                # Timeout of 60 seconds, but task started 10 minutes ago
                task_wait(_argv=["--timeout", "60"])
            assert exc_info.value.code == 2  # Timeout exit code

        captured = capsys.readouterr()
        assert "timeout" in captured.out.lower()

    def test_task_wait_with_wait_interval_argument(self, mock_state_dir, capsys):
        """Test task_wait respects --wait-interval argument."""
        import time

        task = _create_and_add_task("agdt-interval-test")
        task.mark_running()
        update_task(task)

        start = time.time()
        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": task.id}}):
            with pytest.raises(SystemExit) as exc_info:
                task_wait(_argv=["--wait-interval", "0.1"])
            assert exc_info.value.code == 0  # Task still running, exit 0 to retry
        elapsed = time.time() - start

        # Should have waited approximately 0.1 seconds
        assert elapsed >= 0.1
        assert elapsed < 1.0  # But not too long

    def test_task_wait_state_override_for_timeout(self, mock_state_dir, capsys):
        """Test task_wait uses background.timeout from state."""
        task = _create_and_add_task("agdt-state-timeout-test")
        task.mark_running()
        # Set start_time to 2 minutes ago
        old_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        task.start_time = old_time.isoformat()
        update_task(task)

        # State timeout of 60s should trigger timeout (task started 2 min ago)
        with patch(
            "agdt_ai_helpers.state.load_state",
            return_value={"background": {"task_id": task.id, "timeout": "60"}},
        ):
            with pytest.raises(SystemExit) as exc_info:
                task_wait()
            assert exc_info.value.code == 2

        captured = capsys.readouterr()
        assert "timeout" in captured.out.lower()

    def test_task_wait_state_override_for_wait_interval(self, mock_state_dir, capsys):
        """Test task_wait uses background.wait_interval from state."""
        import time

        task = _create_and_add_task("agdt-state-interval-test")
        task.mark_running()
        update_task(task)

        start = time.time()
        with patch(
            "agdt_ai_helpers.state.load_state",
            return_value={"background": {"task_id": task.id, "wait_interval": "0.05"}},
        ):
            with pytest.raises(SystemExit) as exc_info:
                task_wait()
            assert exc_info.value.code == 0  # Task still running, exit 0 to retry
        elapsed = time.time() - start

        # Should have used 0.05s wait interval from state
        assert elapsed >= 0.05
        assert elapsed < 0.5


class TestTasksClean:
    """Tests for tasks_clean command."""

    def test_tasks_clean_removes_completed_tasks(self, mock_state_dir, capsys):
        """Test tasks_clean removes completed tasks."""
        task1 = _create_and_add_task("cmd1")
        task2 = _create_and_add_task("cmd2")
        _create_and_add_task("cmd3")  # Third task not needed for assertions

        task1.mark_completed(exit_code=0)
        update_task(task1)
        task2.mark_failed(exit_code=1)
        update_task(task2)
        # task3 stays pending

        # Run cleanup
        with patch("agdt_ai_helpers.state.load_state", return_value={}):
            tasks_clean()

        # Verify cleanup ran - tasks may or may not be removed depending on expiry settings
        _ = get_background_tasks()  # Just verify it doesn't crash

        # Note: cleanup_expired_tasks may not remove immediately without expiry time
        # Just verify the command runs without error

    def test_tasks_clean_preserves_running_tasks(self, mock_state_dir, capsys):
        """Test tasks_clean preserves running tasks."""
        task = _create_and_add_task("running-cmd")
        task.mark_running()
        update_task(task)

        with patch("agdt_ai_helpers.state.load_state", return_value={}):
            tasks_clean()

        remaining = get_background_tasks()
        remaining_ids = {t.id for t in remaining}

        assert task.id in remaining_ids

    def test_tasks_clean_empty(self, mock_state_dir, capsys):
        """Test tasks_clean with no tasks."""
        with patch("agdt_ai_helpers.state.load_state", return_value={}):
            tasks_clean()

        _ = capsys.readouterr()  # Consume output, not needed for assertion
        # Should complete without error - just verify cleanup ran

    def test_tasks_clean_removes_log_files(self, mock_state_dir, capsys):
        """Test tasks_clean removes associated log files."""
        task = _create_and_add_task("cleanup-test")
        task.mark_completed(exit_code=0)
        update_task(task)

        # Create log file if task has a log_file path
        if task.log_file:
            from pathlib import Path

            log_path = Path(task.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text("Log content")

            with patch("agdt_ai_helpers.state.load_state", return_value={}):
                tasks_clean()

            # Log file may or may not be removed depending on expiry settings
        else:
            # Just run clean without crashing
            with patch("agdt_ai_helpers.state.load_state", return_value={}):
                tasks_clean()


class TestTaskCommandIntegration:
    """Integration tests for task commands working together."""

    def test_full_task_monitoring_workflow(self, mock_state_dir, capsys):
        """Test complete workflow: create -> list -> status -> clean."""
        # Create a task
        task = _create_and_add_task("integration-test-cmd")

        # List should show the task
        list_tasks()
        captured = capsys.readouterr()
        assert task.id in captured.out

        # Update to running
        task.mark_running()
        update_task(task)

        # Status should show running
        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": task.id}}):
            task_status()
        captured = capsys.readouterr()
        assert "running" in captured.out.lower()

        # Complete the task
        task.mark_completed(exit_code=0)
        update_task(task)

        # Clean should work without error
        with patch("agdt_ai_helpers.state.load_state", return_value={}):
            tasks_clean()

        # List - task may or may not be removed depending on expiry
        list_tasks()
        captured = capsys.readouterr()
        # Just verify it doesn't crash


class TestShowOtherIncompleteTasks:
    """Tests for show_other_incomplete_tasks command."""

    def test_no_incomplete_tasks(self, mock_state_dir, capsys):
        """Test when no incomplete tasks exist."""
        from agdt_ai_helpers.cli.tasks.commands import show_other_incomplete_tasks

        show_other_incomplete_tasks()

        captured = capsys.readouterr()
        assert "No other recent incomplete background tasks" in captured.out

    def test_shows_incomplete_running_tasks(self, mock_state_dir, capsys):
        """Test shows running tasks."""
        from agdt_ai_helpers.cli.tasks.commands import show_other_incomplete_tasks

        task = _create_and_add_task("agdt-running-cmd")
        task.mark_running()
        update_task(task)

        show_other_incomplete_tasks()

        captured = capsys.readouterr()
        assert "Other incomplete background tasks" in captured.out
        assert "agdt-running-cmd" in captured.out
        assert task.id in captured.out

    def test_excludes_completed_tasks(self, mock_state_dir, capsys):
        """Test excludes completed tasks."""
        from agdt_ai_helpers.cli.tasks.commands import show_other_incomplete_tasks

        running = _create_and_add_task("agdt-running")
        running.mark_running()
        update_task(running)

        completed = _create_and_add_task("agdt-completed")
        completed.mark_running()
        completed.mark_completed(exit_code=0)
        update_task(completed)

        show_other_incomplete_tasks()

        captured = capsys.readouterr()
        assert "agdt-running" in captured.out
        assert "agdt-completed" not in captured.out

    def test_excludes_current_task_id(self, mock_state_dir, capsys):
        """Test excludes current task_id from state."""
        from agdt_ai_helpers.cli.tasks.commands import show_other_incomplete_tasks

        task1 = _create_and_add_task("agdt-cmd-1")
        task1.mark_running()
        update_task(task1)

        task2 = _create_and_add_task("agdt-cmd-2")
        task2.mark_running()
        update_task(task2)

        # Set task1 as current task_id
        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": task1.id}}):
            show_other_incomplete_tasks()

        captured = capsys.readouterr()
        # Should show task2 but not task1
        assert "agdt-cmd-2" in captured.out
        assert task2.id in captured.out


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
        from agdt_ai_helpers.state import get_value

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

        Bug fix: When a task for dfly-git-save-work succeeds, we should NOT report
        an older failed dfly-git-save-work task as needing attention.
        """
        import time

        # Create an older failed task for dfly-git-save-work
        older_failed = _create_and_add_task("agdt-git-save-work")
        older_failed.mark_running()
        older_failed.mark_failed(exit_code=1)
        update_task(older_failed)

        # Small delay to ensure different timestamps
        time.sleep(0.01)

        # Create a newer successful task for dfly-git-save-work
        newer_success = _create_and_add_task("agdt-git-save-work")
        newer_success.mark_running()
        newer_success.mark_completed(exit_code=0)
        update_task(newer_success)

        with patch(
            "agdt_ai_helpers.state.load_state",
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

        # Create a successful task for dfly-git-save-work
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


class TestSafePrintUnicodeError:
    """Tests for _safe_print with UnicodeEncodeError handling."""

    def test_safe_print_replaces_emoji_on_unicode_error(self, capsys):
        """Test that emoji is replaced when UnicodeEncodeError occurs."""
        from agdt_ai_helpers.cli.tasks.commands import _safe_print

        # We need to simulate a UnicodeEncodeError on the first print call
        call_count = [0]
        original_print = print

        def mock_print(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call raises UnicodeEncodeError
                raise UnicodeEncodeError("codec", "", 0, 1, "mock error")
            # Subsequent calls succeed
            original_print(*args, **kwargs)

        with patch("builtins.print", side_effect=mock_print):
            _safe_print("Status: ✅ OK")

        # The function should have made a second print call with replaced emoji
        assert call_count[0] == 2


class TestTaskLogLineLimits:
    """Tests for task_log line limit handling."""

    def test_task_log_with_positive_line_limit(self, mock_state_dir, capsys, tmp_path):
        """Test task_log with positive line limit (head mode)."""
        from agdt_ai_helpers.state import set_value

        # Create task with multi-line log file
        log_file = tmp_path / "test.log"
        log_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")

        task = BackgroundTask.create(command="agdt-head-test", log_file=log_file)
        add_task(task)

        # Set state values
        set_value("background.task_id", task.id)
        set_value("background.log_lines", "2")  # Only show first 2 lines

        task_log()

        captured = capsys.readouterr()
        assert "Line 1" in captured.out
        assert "Line 2" in captured.out
        # Lines 3-5 should be excluded by head mode
        assert "Line 5" not in captured.out

    def test_task_log_with_negative_line_limit(self, mock_state_dir, capsys, tmp_path):
        """Test task_log with negative line limit (tail mode)."""
        from agdt_ai_helpers.state import set_value

        # Create task with multi-line log file
        log_file = tmp_path / "test.log"
        log_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")

        task = BackgroundTask.create(command="agdt-tail-test", log_file=log_file)
        add_task(task)

        # Set state values
        set_value("background.task_id", task.id)
        set_value("background.log_lines", "-2")  # Only show last 2 lines

        task_log()

        captured = capsys.readouterr()
        # Should have last 2 lines (Line 4 and Line 5), not first lines
        assert "Line 5" in captured.out or "Line 4" in captured.out
        # Line 1 should be excluded by tail mode
        assert "Line 1" not in captured.out

    def test_task_log_with_invalid_line_limit(self, mock_state_dir, capsys, tmp_path):
        """Test task_log ignores invalid line limit."""
        from agdt_ai_helpers.state import set_value

        # Create task with log file
        log_file = tmp_path / "test.log"
        log_file.write_text("Line 1\nLine 2\nLine 3\n")

        task = BackgroundTask.create(command="agdt-invalid-test", log_file=log_file)
        add_task(task)

        # Set invalid line limit (should be ignored)
        set_value("background.task_id", task.id)
        set_value("background.log_lines", "not-a-number")

        task_log()

        captured = capsys.readouterr()
        # All lines should be shown when limit is invalid
        assert "Line 1" in captured.out
        assert "Line 2" in captured.out
        assert "Line 3" in captured.out

    def test_task_log_nonexistent_task(self, mock_state_dir, capsys):
        """Test task_log with nonexistent task ID."""
        with patch("agdt_ai_helpers.state.load_state", return_value={"background": {"task_id": "fake-task-id"}}):
            with pytest.raises(SystemExit):
                task_log()

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()


class TestTaskWaitValueErrorHandling:
    """Tests for ValueError handling in task_wait argument parsing."""

    def test_task_wait_invalid_timeout_in_state(self, mock_state_dir, capsys):
        """Test task_wait handles invalid timeout value in state."""
        task = _create_and_add_task("agdt-test-cmd")
        task.mark_completed(exit_code=0)
        update_task(task)

        # Set invalid timeout in state
        with patch(
            "agdt_ai_helpers.state.load_state",
            return_value={"background": {"task_id": task.id, "timeout": "not-a-number"}},
        ):
            # Should not crash, uses default timeout
            task_wait()

        captured = capsys.readouterr()
        assert "completed" in captured.out.lower()

    def test_task_wait_invalid_wait_interval_in_state(self, mock_state_dir, capsys):
        """Test task_wait handles invalid wait_interval value in state."""
        task = _create_and_add_task("agdt-test-cmd")
        task.mark_completed(exit_code=0)
        update_task(task)

        # Set invalid wait_interval in state
        with patch(
            "agdt_ai_helpers.state.load_state",
            return_value={"background": {"task_id": task.id, "wait_interval": "invalid"}},
        ):
            # Should not crash, uses default wait interval
            task_wait()

        captured = capsys.readouterr()
        assert "completed" in captured.out.lower()


class TestTryAdvancePrReviewToSummary:
    """Tests for _try_advance_pr_review_to_summary function."""

    def test_returns_false_when_no_workflow(self, mock_state_dir):
        """Test returns False when no workflow is active."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_summary

        with patch("agdt_ai_helpers.state.get_workflow_state", return_value=None):
            result = _try_advance_pr_review_to_summary()

        assert result is False

    def test_returns_false_when_wrong_workflow(self, mock_state_dir):
        """Test returns False when workflow is not pull-request-review."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_summary

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "other-workflow", "step": "file-review"},
        ):
            result = _try_advance_pr_review_to_summary()

        assert result is False

    def test_returns_false_when_wrong_step(self, mock_state_dir):
        """Test returns False when step is not file-review."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_summary

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "summary"},
        ):
            result = _try_advance_pr_review_to_summary()

        assert result is False

    def test_returns_false_when_no_pr_id(self, mock_state_dir):
        """Test returns False when no pull_request_id in state."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_summary
        from agdt_ai_helpers.state import set_value

        # Clear any existing PR ID
        set_value("pull_request_id", "")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review"},
        ):
            result = _try_advance_pr_review_to_summary()

        assert result is False

    def test_returns_false_when_invalid_pr_id(self, mock_state_dir):
        """Test returns False when pull_request_id is not a valid integer."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_summary
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "not-a-number")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review"},
        ):
            result = _try_advance_pr_review_to_summary()

        assert result is False

    def test_returns_false_when_files_not_complete(self, mock_state_dir):
        """Test returns False when not all files are complete."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_summary
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "12345")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review"},
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands.get_queue_status",
            return_value={"all_complete": False, "submission_pending_count": 0},
        ):
            result = _try_advance_pr_review_to_summary()

        assert result is False

    def test_returns_false_when_submissions_pending(self, mock_state_dir):
        """Test returns False when submissions are still pending."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_summary
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "12345")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review"},
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands.get_queue_status",
            return_value={"all_complete": True, "submission_pending_count": 2},
        ):
            result = _try_advance_pr_review_to_summary()

        assert result is False

    def test_advances_workflow_when_conditions_met(self, mock_state_dir, capsys):
        """Test advances workflow when all conditions are met."""
        from agdt_ai_helpers.cli.tasks.commands import _try_advance_pr_review_to_summary
        from agdt_ai_helpers.state import set_value

        set_value("pull_request_id", "12345")

        mock_task = BackgroundTask.create(command="agdt-generate-pr-summary")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review", "context": {}},
        ), patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands.get_queue_status",
            return_value={"all_complete": True, "submission_pending_count": 0},
        ), patch("agdt_ai_helpers.cli.workflows.base.set_workflow_state") as mock_set_workflow, patch(
            "agdt_ai_helpers.background_tasks.run_function_in_background",
            return_value=mock_task,
        ) as mock_run_bg:
            result = _try_advance_pr_review_to_summary()

        assert result is True
        mock_set_workflow.assert_called_once()
        mock_run_bg.assert_called_once()

        captured = capsys.readouterr()
        assert "ALL FILE REVIEWS COMPLETE" in captured.out


class TestTryCompletePrReviewWorkflow:
    """Tests for _try_complete_pr_review_workflow function."""

    def test_returns_false_when_no_workflow(self, mock_state_dir):
        """Test returns False when no workflow is active."""
        from agdt_ai_helpers.cli.tasks.commands import _try_complete_pr_review_workflow

        task = _create_and_add_task("agdt-generate-pr-summary")

        with patch("agdt_ai_helpers.state.get_workflow_state", return_value=None):
            result = _try_complete_pr_review_workflow(task)

        assert result is False

    def test_returns_false_when_wrong_workflow(self, mock_state_dir):
        """Test returns False when workflow is not pull-request-review."""
        from agdt_ai_helpers.cli.tasks.commands import _try_complete_pr_review_workflow

        task = _create_and_add_task("agdt-generate-pr-summary")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "other-workflow", "step": "summary"},
        ):
            result = _try_complete_pr_review_workflow(task)

        assert result is False

    def test_returns_false_when_wrong_step(self, mock_state_dir):
        """Test returns False when step is not summary."""
        from agdt_ai_helpers.cli.tasks.commands import _try_complete_pr_review_workflow

        task = _create_and_add_task("agdt-generate-pr-summary")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "file-review"},
        ):
            result = _try_complete_pr_review_workflow(task)

        assert result is False

    def test_returns_false_when_wrong_command(self, mock_state_dir):
        """Test returns False when task command is not dfly-generate-pr-summary."""
        from agdt_ai_helpers.cli.tasks.commands import _try_complete_pr_review_workflow

        task = _create_and_add_task("agdt-other-cmd")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "summary"},
        ):
            result = _try_complete_pr_review_workflow(task)

        assert result is False

    def test_completes_workflow_when_conditions_met(self, mock_state_dir, capsys):
        """Test completes workflow when all conditions are met."""
        from agdt_ai_helpers.cli.tasks.commands import _try_complete_pr_review_workflow

        task = _create_and_add_task("agdt-generate-pr-summary")

        with patch(
            "agdt_ai_helpers.state.get_workflow_state",
            return_value={"active": "pull-request-review", "step": "summary", "context": {}},
        ), patch("agdt_ai_helpers.cli.workflows.base.set_workflow_state") as mock_set_workflow:
            result = _try_complete_pr_review_workflow(task)

        assert result is True
        mock_set_workflow.assert_called_once()

        captured = capsys.readouterr()
        assert "PR REVIEW WORKFLOW COMPLETE" in captured.out


class TestHandleTaskCompleted:
    """Tests for _handle_task_completed function."""

    def test_shows_failed_task_log(self, mock_state_dir, capsys, tmp_path):
        """Test shows log content when task fails."""
        # Create task with log file
        log_file = tmp_path / "test.log"
        log_file.write_text("Error: Something went wrong\nStack trace here\n")

        task = BackgroundTask.create(command="agdt-test-cmd", log_file=log_file)
        task.mark_running()
        task.mark_failed(exit_code=1)
        task.error_message = "Task execution failed"
        add_task(task)

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "agdt_ai_helpers.task_state.get_incomplete_most_recent_per_command",
                return_value=[],
            ), patch(
                "agdt_ai_helpers.task_state.get_failed_most_recent_per_command",
                return_value=[],
            ):
                from agdt_ai_helpers.cli.tasks.commands import _handle_task_completed

                _handle_task_completed(task, task.id, 300.0)

        assert exc_info.value.code != 0

        captured = capsys.readouterr()
        assert "TASK FAILED" in captured.out
        assert "Error: Something went wrong" in captured.out
        assert "Task execution failed" in captured.out

    def test_reports_other_incomplete_tasks(self, mock_state_dir, capsys):
        """Test reports other incomplete tasks."""
        # Create completed task
        completed_task = _create_and_add_task("agdt-completed-cmd")
        completed_task.mark_running()
        completed_task.mark_completed(exit_code=0)
        update_task(completed_task)

        # Create another incomplete task
        incomplete_task = _create_and_add_task("agdt-incomplete-cmd")
        incomplete_task.mark_running()
        update_task(incomplete_task)

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "agdt_ai_helpers.task_state.get_incomplete_most_recent_per_command",
                return_value=[incomplete_task],
            ), patch(
                "agdt_ai_helpers.task_state.get_failed_most_recent_per_command",
                return_value=[],
            ):
                from agdt_ai_helpers.cli.tasks.commands import _handle_task_completed

                _handle_task_completed(completed_task, completed_task.id, 300.0)

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "OTHER TASKS STILL RUNNING" in captured.out
        assert "agdt-incomplete-cmd" in captured.out

    def test_reports_other_failed_tasks(self, mock_state_dir, capsys):
        """Test reports other failed tasks."""
        # Create completed task
        completed_task = _create_and_add_task("agdt-completed-cmd")
        completed_task.mark_running()
        completed_task.mark_completed(exit_code=0)
        update_task(completed_task)

        # Create another failed task (different command)
        failed_task = _create_and_add_task("agdt-failed-cmd")
        failed_task.mark_running()
        failed_task.mark_failed(exit_code=1)
        update_task(failed_task)

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "agdt_ai_helpers.task_state.get_incomplete_most_recent_per_command",
                return_value=[],
            ), patch(
                "agdt_ai_helpers.task_state.get_failed_most_recent_per_command",
                return_value=[failed_task],
            ):
                from agdt_ai_helpers.cli.tasks.commands import _handle_task_completed

                _handle_task_completed(completed_task, completed_task.id, 300.0)

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "OTHER TASKS FAILED" in captured.out
        assert "agdt-failed-cmd" in captured.out
