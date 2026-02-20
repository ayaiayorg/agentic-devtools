"""
Tests for file_locking module.
"""

from agentic_devtools.file_locking import (
    lock_file,
    unlock_file,
)


class TestLockFile:
    """Tests for lock_file function."""

    def test_lock_file_creates_lock(self, tmp_path):
        """Test lock_file successfully locks a file handle."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with open(test_file, "r+") as f:
            # Should not raise
            lock_file(f, exclusive=True, timeout=1.0)
            unlock_file(f)

    def test_lock_file_shared_mode(self, tmp_path):
        """Test lock_file in shared (read) mode."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with open(test_file) as f:
            # Should not raise for shared lock
            lock_file(f, exclusive=False, timeout=1.0)
            unlock_file(f)
