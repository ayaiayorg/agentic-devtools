"""Tests for agentic_devtools.cli.state.get_cmd."""

import sys
from io import StringIO
from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import state as cli_state


class TestGetCommand:
    """Tests for agdt-get command."""

    def test_get_existing_value(self, temp_state_dir, clear_state_before):
        """Test getting an existing value."""
        state.set_value("test", "value")
        with patch.object(sys, "argv", ["agdt-get", "test"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                cli_state.get_cmd()
                assert mock_stdout.getvalue().strip() == "value"

    def test_get_nonexistent_exits(self, temp_state_dir, clear_state_before):
        """Test getting nonexistent key exits with error."""
        with patch.object(sys, "argv", ["agdt-get", "nonexistent"]):
            with pytest.raises(SystemExit) as exc_info:
                cli_state.get_cmd()
            assert exc_info.value.code == 1

    def test_get_json_value_pretty_printed(self, temp_state_dir, clear_state_before):
        """Test getting a JSON value is pretty printed."""
        state.set_value("config", {"key": "value"})
        with patch.object(sys, "argv", ["agdt-get", "config"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                cli_state.get_cmd()
                output = mock_stdout.getvalue()
                assert '"key"' in output
                assert '"value"' in output

    def test_get_cmd_missing_key_exits_with_error(self, temp_state_dir):
        """Test that get_cmd exits with error when no key provided."""
        with patch("sys.argv", ["agdt-get"]):
            with pytest.raises(SystemExit) as exc_info:
                cli_state.get_cmd()
            assert exc_info.value.code == 1
