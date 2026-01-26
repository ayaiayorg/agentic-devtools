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


class TestLockedFile:
    """Tests for locked_file context manager."""

    def test_locked_file_read_write(self, tmp_path):
        """Test locked_file context manager for read/write."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("initial content")

        with locked_file(test_file, mode="r+", exclusive=True) as f:
            content = f.read()
            assert content == "initial content"

    def test_locked_file_creates_parent_dirs(self, tmp_path):
        """Test locked_file creates parent directories if needed."""
        test_file = tmp_path / "subdir" / "nested" / "test.txt"

        with locked_file(test_file, mode="w", exclusive=True) as f:
            f.write("test")

        assert test_file.exists()

    def test_locked_file_creates_file_if_needed(self, tmp_path):
        """Test locked_file creates file with empty JSON for r+ mode."""
        test_file = tmp_path / "new_file.json"
        assert not test_file.exists()

        with locked_file(test_file, mode="r+", exclusive=True) as f:
            content = f.read()
            assert content == "{}"

    def test_locked_file_releases_on_exit(self, tmp_path):
        """Test locked_file releases lock when exiting context."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        with locked_file(test_file, mode="r+"):
            pass

        # Should be able to lock again after context exits
        with locked_file(test_file, mode="r+"):
            pass

    def test_locked_file_releases_on_exception(self, tmp_path):
        """Test locked_file releases lock even on exception."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        with pytest.raises(ValueError):
            with locked_file(test_file, mode="r+"):
                raise ValueError("test error")

        # Should still be able to lock after exception
        with locked_file(test_file, mode="r+"):
            pass

    def test_locked_file_shared_lock(self, tmp_path):
        """Test locked_file with shared (non-exclusive) lock."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        with locked_file(test_file, mode="r", exclusive=False) as f:
            content = f.read()
            assert content == "content"


class TestLockedStateFile:
    """Tests for locked_state_file context manager."""

    def test_locked_state_file_creates_empty_json(self, tmp_path):
        """Test locked_state_file creates file with empty JSON if not exists."""
        state_file = tmp_path / "state.json"
        assert not state_file.exists()

        with locked_state_file(state_file) as f:
            content = f.read()
            assert content == "{}"

    def test_locked_state_file_reads_existing(self, tmp_path):
        """Test locked_state_file reads existing state file."""
        state_file = tmp_path / "state.json"
        state_file.write_text('{"key": "value"}')

        with locked_state_file(state_file) as f:
            content = f.read()
            assert content == '{"key": "value"}'

    def test_locked_state_file_exclusive_lock(self, tmp_path):
        """Test locked_state_file uses exclusive lock."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}")

        # Use context manager successfully
        with locked_state_file(state_file) as f:
            # We can read and write
            f.read()

    def test_locked_state_file_releases_on_exit(self, tmp_path):
        """Test locked_state_file releases lock on context exit."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}")

        with locked_state_file(state_file):
            pass

        # Should be able to acquire again
        with locked_state_file(state_file):
            pass

    def test_locked_state_file_releases_on_exception(self, tmp_path):
        """Test locked_state_file releases lock even on exception."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}")

        with pytest.raises(ValueError):
            with locked_state_file(state_file):
                raise ValueError("test")

        # Should still be able to acquire
        with locked_state_file(state_file):
            pass

    def test_locked_state_file_creates_parent_dirs(self, tmp_path):
        """Test locked_state_file creates parent directories."""
        state_file = tmp_path / "subdir" / "state.json"

        with locked_state_file(state_file) as f:
            assert f is not None

        assert state_file.parent.exists()

    def test_locked_state_file_with_timeout(self, tmp_path):
        """Test locked_state_file accepts timeout parameter."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}")

        # Should work with custom timeout
        with locked_state_file(state_file, timeout=2.0):
            pass


class TestFileLockError:
    """Tests for FileLockError exception."""

    def test_file_lock_error_is_exception(self):
        """Test FileLockError is an Exception subclass."""
        assert issubclass(FileLockError, Exception)

    def test_file_lock_error_message(self):
        """Test FileLockError can be raised with message."""
        with pytest.raises(FileLockError) as exc_info:
            raise FileLockError("Could not acquire lock")

        assert "Could not acquire lock" in str(exc_info.value)


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


class TestLockedFileEdgeCases:
    """Tests for edge cases in locked_file context manager."""

    def test_locked_file_with_binary_mode(self, tmp_path):
        """Test locked_file with binary mode (no encoding)."""
        test_file = tmp_path / "binary.bin"
        test_file.write_bytes(b"binary data")

        with locked_file(test_file, mode="rb", exclusive=False, encoding=None) as f:
            content = f.read()
            assert content == b"binary data"

    def test_locked_file_write_only_mode(self, tmp_path):
        """Test locked_file with write-only mode."""
        test_file = tmp_path / "write.txt"

        with locked_file(test_file, mode="w", exclusive=True) as f:
            f.write("new content")

        assert test_file.read_text() == "new content"

    def test_locked_file_creates_deeply_nested_dirs(self, tmp_path):
        """Test locked_file creates multiple levels of parent directories."""
        test_file = tmp_path / "a" / "b" / "c" / "d" / "test.txt"

        with locked_file(test_file, mode="w", exclusive=True) as f:
            f.write("deep")

        assert test_file.exists()
        assert test_file.read_text() == "deep"
