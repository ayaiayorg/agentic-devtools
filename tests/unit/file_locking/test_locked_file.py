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
