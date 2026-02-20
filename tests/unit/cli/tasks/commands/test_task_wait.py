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
    task_wait,
)
from agdt_ai_helpers.task_state import (
    BackgroundTask,
    add_task,
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
