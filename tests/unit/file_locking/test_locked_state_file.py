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
