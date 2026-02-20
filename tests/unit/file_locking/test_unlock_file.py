"""
Tests for file_locking module.
"""

import pytest

from agentic_devtools.file_locking import (
    FileLockError,
    lock_file,
    locked_file,
    locked_state_file,
    unlock_file,
)


class TestUnlockFile:
    """Tests for unlock_file function."""

    def test_unlock_file_releases_lock(self, tmp_path):
        """Test unlock_file releases the lock."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with open(test_file, "r+") as f:
            lock_file(f, exclusive=True, timeout=1.0)
            unlock_file(f)
            # Should be able to lock again after unlock
            lock_file(f, exclusive=True, timeout=1.0)
            unlock_file(f)
