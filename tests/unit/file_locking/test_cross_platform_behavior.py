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


class TestCrossPlatformBehavior:
    """Tests for cross-platform lock behavior."""

    def test_lock_persists_through_context(self, tmp_path):
        """Test that lock is held for duration of context."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}")

        operations_in_context = []

        with locked_state_file(state_file) as f:
            operations_in_context.append("read")
            # Read through the locked file handle, not directly from path
            # (Windows doesn't allow reading a file with exclusive lock via separate handle)
            _ = f.read()  # Read to advance position, but value not needed
            operations_in_context.append("process")
            # Seek back and write through the locked handle
            f.seek(0)
            f.write('{"updated": true}')
            f.truncate()
            operations_in_context.append("write")

        assert operations_in_context == ["read", "process", "write"]
        assert state_file.read_text() == '{"updated": true}'
