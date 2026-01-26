"""
Tests for background_tasks module.

Tests use the actual task_state API:
- BackgroundTask.create() (not constructor with task_id)
- task.id (not task.task_id)
- task.start_time (not task.created_at)
- get_task_by_id() (not get_task())
- get_task_log_content(task_id: str) (not task object)
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.background_tasks import (
    cleanup_old_logs,
    get_task_log_content,
    run_in_background,
    wait_for_task,
)
from agentic_devtools.task_state import (
    BackgroundTask,
    TaskStatus,
    add_task,
    get_task_by_id,
)


@pytest.fixture
def mock_state_dir(tmp_path):
    """Fixture to mock the state directory."""
    # Need to patch in both modules since task_state imports get_state_dir
    with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path), patch(
        "agentic_devtools.task_state.get_state_dir", return_value=tmp_path
    ):
        yield tmp_path


class TestRunInBackground:
    """Tests for run_in_background function."""

    def test_returns_background_task(self, mock_state_dir):
        """Test run_in_background returns a BackgroundTask."""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            task = run_in_background("echo hello")

        assert isinstance(task, BackgroundTask)
        assert task.command == "echo hello"

    def test_task_has_unique_id(self, mock_state_dir):
        """Test each background task gets a unique ID."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(pid=1)

            task1 = run_in_background("cmd1")
            task2 = run_in_background("cmd2")

        assert task1.id != task2.id

    def test_creates_log_directory(self, mock_state_dir):
        """Test log directory is created (by get_logs_dir during task creation)."""
        from agentic_devtools.background_tasks import get_logs_dir

        # Force logs dir creation by calling the function
        logs_dir = get_logs_dir()

        assert logs_dir.exists()
        assert logs_dir.name == "logs"

    def test_popen_called(self, mock_state_dir):
        """Test subprocess.Popen is called to spawn background process."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(pid=1)

            run_in_background("dfly-test-cmd")

        # Verify Popen was called (with Python wrapper script)
        mock_popen.assert_called_once()

    def test_task_saved_with_pending_status(self, mock_state_dir):
        """Test task is saved with pending status after spawn (running status set by subprocess)."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(pid=1)

            task = run_in_background("echo")

            # Task should be pending (subprocess will set it to running)
            stored_task = get_task_by_id(task.id)
            assert stored_task.status == TaskStatus.PENDING


class TestGetTaskLogContent:
    """Tests for get_task_log_content function."""

    def test_returns_log_content(self, mock_state_dir):
        """Test get_task_log_content returns file content."""
        # Create log file path within mock state dir
        log_path = mock_state_dir / "logs" / "test-task.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("Log line 1\nLog line 2\n")

        # Create a task with the log file
        task = BackgroundTask.create(command="cmd", log_file=log_path)
        add_task(task)

        content = get_task_log_content(task.id)

        assert content is not None
        assert "Log line 1" in content
        assert "Log line 2" in content

    def test_returns_none_for_missing_file(self, mock_state_dir):
        """Test returns None if log file doesn't exist."""
        task = BackgroundTask.create(command="cmd")
        add_task(task)

        # Don't create the log file
        content = get_task_log_content(task.id)

        assert content is None

    def test_returns_none_for_nonexistent_task(self, mock_state_dir):
        """Test returns None for non-existent task ID."""
        content = get_task_log_content("nonexistent-task-id")
        assert content is None

    def test_handles_unicode_content(self, mock_state_dir):
        """Test handles unicode characters in log."""
        # Create log file path within mock state dir
        log_path = mock_state_dir / "logs" / "unicode-task.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("Unicode: äöü 日本語 🎉", encoding="utf-8")

        # Create a task with the log file
        task = BackgroundTask.create(command="cmd", log_file=log_path)
        add_task(task)

        content = get_task_log_content(task.id)

        assert content is not None
        assert "Unicode" in content
        assert "äöü" in content


class TestWaitForTask:
    """Tests for wait_for_task function."""

    def test_returns_immediately_for_completed_task(self, mock_state_dir):
        """Test wait returns immediately for completed task."""
        task = BackgroundTask.create(command="cmd")
        task.mark_completed(exit_code=0)
        add_task(task)

        success, exit_code = wait_for_task(task.id, timeout=1.0)

        assert success is True
        assert exit_code == 0

    def test_returns_immediately_for_failed_task(self, mock_state_dir):
        """Test wait returns immediately for failed task."""
        task = BackgroundTask.create(command="cmd")
        task.mark_failed(exit_code=1)
        add_task(task)

        success, exit_code = wait_for_task(task.id, timeout=1.0)

        assert success is False
        assert exit_code == 1

    def test_returns_none_for_nonexistent_task(self, mock_state_dir):
        """Test wait returns (False, None) for non-existent task."""
        success, exit_code = wait_for_task("nonexistent-task-id", timeout=1.0)

        assert success is False
        assert exit_code is None

    def test_times_out_for_running_task(self, mock_state_dir):
        """Test wait times out for running task."""
        task = BackgroundTask.create(command="cmd")
        task.mark_running()
        add_task(task)

        start = time.time()
        success, exit_code = wait_for_task(task.id, timeout=0.5, poll_interval=0.1)
        elapsed = time.time() - start

        assert success is False
        assert exit_code is None
        assert elapsed >= 0.4  # Should have waited for timeout


class TestCleanupOldLogs:
    """Tests for cleanup_old_logs function."""

    def test_removes_old_logs(self, mock_state_dir):
        """Test cleanup_old_logs removes old log files."""
        from agentic_devtools.background_tasks import get_logs_dir

        logs_dir = get_logs_dir()

        # Create an old log file
        old_log = logs_dir / "old.log"
        old_log.write_text("old content")

        # Make it appear old by setting mtime to the past
        import os

        old_time = time.time() - (25 * 3600)  # 25 hours ago
        os.utime(old_log, (old_time, old_time))

        removed = cleanup_old_logs(max_age_hours=24)

        assert removed >= 1
        assert not old_log.exists()

    def test_preserves_recent_logs(self, mock_state_dir):
        """Test cleanup_old_logs preserves recent log files."""
        from agentic_devtools.background_tasks import get_logs_dir

        logs_dir = get_logs_dir()

        # Create a recent log file
        recent_log = logs_dir / "recent.log"
        recent_log.write_text("recent content")

        removed = cleanup_old_logs(max_age_hours=24)

        assert removed == 0
        assert recent_log.exists()

    def test_handles_empty_log_directory(self, mock_state_dir):
        """Test cleanup handles empty log directory."""
        from agentic_devtools.background_tasks import get_logs_dir

        get_logs_dir()  # Ensure directory exists
        # Directory exists but is empty

        removed = cleanup_old_logs(max_age_hours=24)

        assert removed == 0

    def test_handles_missing_log_directory(self, mock_state_dir):
        """Test cleanup handles missing log directory."""
        # Don't create logs directory
        removed = cleanup_old_logs(max_age_hours=24)

        assert removed == 0

    def test_max_count_deletes_excess_logs(self, mock_state_dir):
        """Test cleanup_old_logs with max_count deletes excess files."""
        from agentic_devtools.background_tasks import get_logs_dir

        logs_dir = get_logs_dir()

        # Create multiple log files with different mtimes
        import os

        for i in range(5):
            log_file = logs_dir / f"test-{i}.log"
            log_file.write_text(f"content {i}")
            # Set progressively older mtimes (but all within last hour)
            mtime = time.time() - (i * 60)  # Each 1 minute older
            os.utime(log_file, (mtime, mtime))

        # Keep only 2 logs, with very high max_age to ensure no age-based deletion
        removed = cleanup_old_logs(max_age_hours=1000, max_count=2)

        # Should have deleted 3 (oldest ones) due to max_count
        assert removed == 3
        remaining = list(logs_dir.glob("*.log"))
        assert len(remaining) == 2

    def test_max_count_handles_oserror_on_delete(self, mock_state_dir):
        """Test cleanup_old_logs handles OSError when deleting excess files."""
        from agentic_devtools.background_tasks import get_logs_dir

        logs_dir = get_logs_dir()

        # Create log files
        for i in range(3):
            log_file = logs_dir / f"test-{i}.log"
            log_file.write_text(f"content {i}")

        # Mock unlink to raise OSError
        with patch("pathlib.Path.unlink", side_effect=OSError("Permission denied")):
            # Should not raise, just return 0 deleted
            removed = cleanup_old_logs(max_age_hours=0, max_count=1)

        # No files deleted due to OSError
        assert removed == 0

    def test_old_logs_oserror_on_stat(self, mock_state_dir, monkeypatch):
        """Test cleanup_old_logs handles OSError when getting file stats."""
        from agentic_devtools.background_tasks import get_logs_dir

        logs_dir = get_logs_dir()

        # Create a log file
        log_file = logs_dir / "test.log"
        log_file.write_text("content")

        # Store original stat method to call only when needed
        original_stat = type(log_file).stat

        # Mock stat to raise OSError for any call on log files
        def mock_stat(self, *args, **kwargs):
            if str(self).endswith(".log"):
                raise OSError("Permission denied")
            return original_stat(self, *args, **kwargs)

        monkeypatch.setattr(type(log_file), "stat", mock_stat)

        # Should not raise, just skip the file
        removed = cleanup_old_logs(max_age_hours=0)

        assert removed == 0


class TestBackgroundTaskIntegration:
    """Integration tests for background task operations."""

    def test_multiple_background_tasks(self, mock_state_dir):
        """Test running multiple background tasks."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(pid=1)

            task1 = run_in_background("cmd1")
            task2 = run_in_background("cmd2")
            task3 = run_in_background("cmd3")

        # All should have unique IDs
        ids = {task1.id, task2.id, task3.id}
        assert len(ids) == 3

        # All should be retrievable
        assert get_task_by_id(task1.id) is not None
        assert get_task_by_id(task2.id) is not None
        assert get_task_by_id(task3.id) is not None
