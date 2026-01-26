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


class TestUnixFileLocking:
    """Tests for Unix-specific file locking using fcntl."""

    @pytest.mark.linux_only
    def test_lock_file_unix_exclusive(self, tmp_path):
        """Test _lock_file_unix acquires exclusive lock."""
        from agentic_devtools.file_locking import _lock_file_unix, _unlock_file_unix

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with open(test_file, "r+") as f:
            _lock_file_unix(f, exclusive=True, timeout=1.0)
            _unlock_file_unix(f)

    @pytest.mark.linux_only
    def test_lock_file_unix_shared(self, tmp_path):
        """Test _lock_file_unix acquires shared lock."""
        from agentic_devtools.file_locking import _lock_file_unix, _unlock_file_unix

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with open(test_file) as f:
            _lock_file_unix(f, exclusive=False, timeout=1.0)
            _unlock_file_unix(f)

    @pytest.mark.linux_only
    def test_lock_file_unix_timeout(self, tmp_path):
        """Test _lock_file_unix raises FileLockError on timeout."""
        from agentic_devtools.file_locking import _lock_file_unix

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Create a mock fcntl module - use sys.modules patching because
        # fcntl is imported inside the function, not at module level
        mock_fcntl = MagicMock()
        mock_fcntl.LOCK_EX = 2
        mock_fcntl.LOCK_SH = 1
        mock_fcntl.LOCK_NB = 4
        mock_fcntl.flock.side_effect = OSError("Resource busy")

        with patch.dict(sys.modules, {"fcntl": mock_fcntl}):
            with open(test_file, "r+") as f:
                with pytest.raises(FileLockError) as exc_info:
                    _lock_file_unix(f, exclusive=True, timeout=0.05)

                assert "Could not acquire lock" in str(exc_info.value)

    @pytest.mark.linux_only
    def test_unlock_file_unix(self, tmp_path):
        """Test _unlock_file_unix releases lock."""
        from agentic_devtools.file_locking import _lock_file_unix, _unlock_file_unix

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with open(test_file, "r+") as f:
            _lock_file_unix(f, exclusive=True, timeout=1.0)
            _unlock_file_unix(f)
            # Should be able to lock again after unlock
            _lock_file_unix(f, exclusive=True, timeout=1.0)
            _unlock_file_unix(f)

    @pytest.mark.linux_only
    def test_lock_file_unix_retry_loop(self, tmp_path):
        """Test _lock_file_unix retries before timing out."""
        from agentic_devtools.file_locking import _lock_file_unix

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        call_count = 0

        def mock_flock(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OSError("Busy")
            # Success on 3rd attempt

        mock_fcntl = MagicMock()
        mock_fcntl.LOCK_EX = 2
        mock_fcntl.LOCK_SH = 1
        mock_fcntl.LOCK_NB = 4
        mock_fcntl.flock.side_effect = mock_flock

        with patch.dict(sys.modules, {"fcntl": mock_fcntl}):
            with open(test_file, "r+") as f:
                _lock_file_unix(f, exclusive=True, timeout=1.0)

        assert call_count == 3

    @pytest.mark.linux_only
    def test_lock_file_unix_uses_correct_lock_type(self, tmp_path):
        """Test _lock_file_unix uses LOCK_EX for exclusive and LOCK_SH for shared."""
        from agentic_devtools.file_locking import _lock_file_unix

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        mock_fcntl = MagicMock()
        mock_fcntl.LOCK_EX = 2
        mock_fcntl.LOCK_SH = 1
        mock_fcntl.LOCK_NB = 4

        with patch.dict(sys.modules, {"fcntl": mock_fcntl}):
            with open(test_file, "r+") as f:
                _lock_file_unix(f, exclusive=True, timeout=1.0)
                # Should use LOCK_EX | LOCK_NB = 2 | 4 = 6
                mock_fcntl.flock.assert_called_with(f.fileno(), 6)

            mock_fcntl.reset_mock()

            with open(test_file) as f:
                _lock_file_unix(f, exclusive=False, timeout=1.0)
                # Should use LOCK_SH | LOCK_NB = 1 | 4 = 5
                mock_fcntl.flock.assert_called_with(f.fileno(), 5)
