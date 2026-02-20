"""
Platform-specific tests for file_locking module.

These tests directly exercise the platform-specific implementations:
- Windows: _lock_file_windows, _unlock_file_windows (msvcrt)
- Linux/Unix: _lock_file_unix, _unlock_file_unix (fcntl)

Cross-platform tests that use the public API (lock_file, unlock_file, etc.)
are in test_file_locking.py and run on both platforms.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.file_locking import FileLockError


class TestWindowsFileLocking:
    """Tests for Windows-specific file locking using msvcrt."""

    @pytest.mark.windows_only
    def test_lock_file_windows_exclusive(self, tmp_path):
        """Test _lock_file_windows acquires exclusive lock."""
        from agentic_devtools.file_locking import _lock_file_windows, _unlock_file_windows

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with open(test_file, "r+") as f:
            _lock_file_windows(f, exclusive=True, timeout=1.0)
            _unlock_file_windows(f)

    @pytest.mark.windows_only
    def test_lock_file_windows_shared(self, tmp_path):
        """Test _lock_file_windows acquires shared lock."""
        from agentic_devtools.file_locking import _lock_file_windows, _unlock_file_windows

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with open(test_file) as f:
            _lock_file_windows(f, exclusive=False, timeout=1.0)
            _unlock_file_windows(f)

    @pytest.mark.windows_only
    def test_lock_file_windows_timeout(self, tmp_path):
        """Test _lock_file_windows raises FileLockError on timeout."""
        from agentic_devtools.file_locking import _lock_file_windows

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Create a mock msvcrt module - use sys.modules patching because
        # msvcrt is imported inside the function, not at module level
        mock_msvcrt = MagicMock()
        mock_msvcrt.LK_NBLCK = 2
        mock_msvcrt.LK_NBRLCK = 3
        mock_msvcrt.locking.side_effect = OSError("Resource busy")

        with patch.dict(sys.modules, {"msvcrt": mock_msvcrt}):
            with open(test_file, "r+") as f:
                with pytest.raises(FileLockError) as exc_info:
                    _lock_file_windows(f, exclusive=True, timeout=0.05)

                assert "Could not acquire lock" in str(exc_info.value)

    @pytest.mark.windows_only
    def test_unlock_file_windows_ignores_errors(self, tmp_path):
        """Test _unlock_file_windows silently ignores unlock errors."""
        from agentic_devtools.file_locking import _unlock_file_windows

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Create a mock msvcrt module that raises on unlock
        mock_msvcrt = MagicMock()
        mock_msvcrt.LK_UNLCK = 0
        mock_msvcrt.locking.side_effect = OSError("Already unlocked")

        with patch.dict(sys.modules, {"msvcrt": mock_msvcrt}):
            with open(test_file, "r+") as f:
                # Should not raise
                _unlock_file_windows(f)

    @pytest.mark.windows_only
    def test_lock_file_windows_retry_loop(self, tmp_path):
        """Test _lock_file_windows retries before timing out."""
        from agentic_devtools.file_locking import _lock_file_windows

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        call_count = 0

        def mock_locking(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OSError("Busy")
            # Success on 3rd attempt

        mock_msvcrt = MagicMock()
        mock_msvcrt.LK_NBLCK = 2
        mock_msvcrt.LK_NBRLCK = 3
        mock_msvcrt.locking.side_effect = mock_locking

        with patch.dict(sys.modules, {"msvcrt": mock_msvcrt}):
            with open(test_file, "r+") as f:
                _lock_file_windows(f, exclusive=True, timeout=1.0)

        assert call_count == 3
