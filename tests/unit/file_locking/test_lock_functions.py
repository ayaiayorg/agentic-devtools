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


class TestLockFunctions:
    """Tests for direct lock/unlock functions."""

    def test_lock_file_with_short_timeout(self, tmp_path):
        """Test lock_file accepts short timeout values."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        with open(test_file, "r+") as f:
            lock_file(f, exclusive=True, timeout=0.1)
            unlock_file(f)

    def test_unlock_file_idempotent(self, tmp_path):
        """Test that unlock_file can be called multiple times safely."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        with open(test_file, "r+") as f:
            lock_file(f, exclusive=True, timeout=1.0)
            unlock_file(f)
            # Second unlock should not raise
            unlock_file(f)
