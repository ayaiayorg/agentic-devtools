"""
Tests for cli/runner.py module.

This module tests the command runner that maps agdt-* commands to their
entry point functions.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from agentic_devtools.cli import runner


class TestRunAsScript:
    """Tests for the run_as_script function."""

    def test_derives_command_name_from_argv0(self):
        """Test that run_as_script derives command name from sys.argv[0]."""
        mock_func = MagicMock()
        mock_module = MagicMock()
        mock_module.show_cmd = mock_func

        with patch("importlib.import_module", return_value=mock_module):
            with patch.object(sys, "argv", ["/usr/bin/agdt-show"]):
                runner.run_as_script()

        mock_func.assert_called_once()

    def test_handles_keyboard_interrupt_with_exit_130(self):
        """Test that run_as_script handles KeyboardInterrupt and exits with 130."""
        with patch("agentic_devtools.cli.runner.run_command") as mock_run:
            mock_run.side_effect = KeyboardInterrupt()
            with patch.object(sys, "argv", ["/usr/bin/agdt-show"]):
                with pytest.raises(SystemExit) as exc_info:
                    runner.run_as_script()
        assert exc_info.value.code == 130

    def test_prints_cancelled_message_on_keyboard_interrupt(self, capsys):
        """Test that run_as_script prints cancellation message on Ctrl+C."""
        with patch("agentic_devtools.cli.runner.run_command") as mock_run:
            mock_run.side_effect = KeyboardInterrupt()
            with patch.object(sys, "argv", ["/usr/bin/agdt-show"]):
                with pytest.raises(SystemExit):
                    runner.run_as_script()
        captured = capsys.readouterr()
        assert "Operation cancelled" in captured.out
