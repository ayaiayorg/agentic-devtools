"""Tests for agentic_devtools.state.load_state."""

from unittest.mock import patch

from agentic_devtools import state
from agentic_devtools.file_locking import FileLockError


class TestLoadState:
    """Tests for load_state function."""

    def test_load_state_returns_dict(self, temp_state_dir):
        """Test that load_state returns a dictionary."""
        state.set_value("test", "value")
        loaded = state.load_state()
        assert isinstance(loaded, dict)
        assert loaded["test"] == "value"

    def test_load_state_handles_corrupt_json(self, temp_state_dir):
        """Test that corrupt JSON returns empty dict."""
        state_file = temp_state_dir / "agdt-state.json"
        state_file.write_text("{ invalid json", encoding="utf-8")

        result = state.load_state()
        assert result == {}

    def test_load_state_with_locking(self, temp_state_dir):
        """Test load_state with use_locking=True."""
        state.save_state({"test_key": "test_value"})

        loaded = state.load_state(use_locking=True)
        assert loaded == {"test_key": "test_value"}

    def test_load_state_filelock_error_fallback(self, temp_state_dir):
        """Test that load_state falls back to unlocked read on FileLockError."""
        state.save_state({"fallback_key": "fallback_value"})

        with patch.object(state, "locked_state_file") as mock_lock:
            mock_lock.side_effect = FileLockError("Lock timeout")

            loaded = state.load_state(use_locking=True)
            assert loaded == {"fallback_key": "fallback_value"}

    def test_load_state_locked_convenience(self, temp_state_dir):
        """Test load_state_locked convenience function."""
        state.save_state({"key": "value"})

        loaded = state.load_state_locked()
        assert loaded == {"key": "value"}
