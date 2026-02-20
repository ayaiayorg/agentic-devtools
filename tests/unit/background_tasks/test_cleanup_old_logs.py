"""Tests for agentic_devtools.background_tasks.cleanup_old_logs."""

import os
import time
from unittest.mock import patch

import pytest

from agentic_devtools.background_tasks import cleanup_old_logs


@pytest.fixture
def mock_state_dir(tmp_path):
    """Fixture to mock the state directory."""
    with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path), patch(
        "agentic_devtools.task_state.get_state_dir", return_value=tmp_path
    ):
        yield tmp_path


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

    def test_creates_log_directory_when_missing(self, mock_state_dir):
        """Test cleanup creates log directory when it is initially missing and deletes nothing."""
        from agentic_devtools.background_tasks import get_logs_dir

        # Don't create logs directory explicitly; cleanup_old_logs should ensure it exists
        removed = cleanup_old_logs(max_age_hours=24)

        assert removed == 0
        assert get_logs_dir().exists()

    def test_max_count_deletes_excess_logs(self, mock_state_dir):
        """Test cleanup_old_logs with max_count deletes excess files."""
        from agentic_devtools.background_tasks import get_logs_dir

        logs_dir = get_logs_dir()

        # Create multiple log files with different mtimes
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
