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
