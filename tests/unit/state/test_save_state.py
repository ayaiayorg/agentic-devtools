"""Tests for agentic_devtools.state.save_state."""

from unittest.mock import patch

from agentic_devtools import state
from agentic_devtools.file_locking import FileLockError


class TestSaveState:
    """Tests for save_state function."""

    def test_save_state_with_locking(self, temp_state_dir):
        """Test save_state with use_locking=True."""
        state.save_state({"locked_key": "locked_value"}, use_locking=True)

        loaded = state.load_state()
        assert loaded == {"locked_key": "locked_value"}

    def test_save_state_filelock_error_fallback(self, temp_state_dir):
        """Test that save_state falls back to unlocked write on FileLockError."""
        with patch.object(state, "locked_state_file") as mock_lock:
            mock_lock.side_effect = FileLockError("Lock timeout")

            state.save_state({"fallback_save": "value"}, use_locking=True)

            loaded = state.load_state()
            assert loaded == {"fallback_save": "value"}
