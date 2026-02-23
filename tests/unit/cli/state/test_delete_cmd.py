"""Tests for agentic_devtools.cli.state.delete_cmd."""

import sys
from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import state as cli_state


class TestDeleteCommand:
    """Tests for agdt-delete command."""

    def test_delete_existing_key(self, temp_state_dir, clear_state_before):
        """Test deleting an existing key."""
        state.set_value("to_delete", "value")
        with patch.object(sys, "argv", ["agdt-delete", "to_delete"]):
            cli_state.delete_cmd()
        assert state.get_value("to_delete") is None

    def test_delete_nonexistent_key(self, temp_state_dir, clear_state_before):
        """Test deleting a nonexistent key (no error, just message)."""
        with patch.object(sys, "argv", ["agdt-delete", "nonexistent"]):
            cli_state.delete_cmd()

    def test_delete_cmd_missing_key_exits_with_error(self, temp_state_dir):
        """Test that delete_cmd exits with error when no key provided."""
        with patch("sys.argv", ["agdt-delete"]):
            with pytest.raises(SystemExit) as exc_info:
                cli_state.delete_cmd()
            assert exc_info.value.code == 1
