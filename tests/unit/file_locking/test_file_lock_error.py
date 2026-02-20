"""
Tests for file_locking module.
"""

import pytest

from agentic_devtools.file_locking import (
    FileLockError,
)


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
