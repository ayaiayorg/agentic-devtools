"""
Tests for cli/runner.py module.

This module tests the command runner that maps agdt-* commands to their
entry point functions.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli import runner


class TestMain:
    """Tests for the main function."""

    def test_exits_with_help_when_no_args(self):
        """Test that main shows help and exits when no args provided."""
        with patch.object(sys, "argv", ["runner"]):
            with pytest.raises(SystemExit) as exc_info:
                runner.main()
        assert exc_info.value.code == 1

    def test_prints_usage_when_no_args(self, capsys):
        """Test that main prints usage info when no args provided."""
        with patch.object(sys, "argv", ["runner"]):
            with pytest.raises(SystemExit):
                runner.main()
        captured = capsys.readouterr()
        assert "Usage:" in captured.out
        assert "agentic_devtools.cli.runner" in captured.out
        assert "Available commands:" in captured.out

    def test_adjusts_sys_argv_before_running_command(self):
        """Test that main adjusts sys.argv so command sees correct args."""
        original_argv = None

        def capture_argv():
            nonlocal original_argv
            original_argv = sys.argv.copy()

        mock_func = MagicMock(side_effect=capture_argv)
        mock_module = MagicMock()
        mock_module.show_cmd = mock_func

        with patch("importlib.import_module", return_value=mock_module):
            with patch.object(sys, "argv", ["runner", "agdt-show", "arg1", "arg2"]):
                runner.main()

        # The command should see argv as: [command_name, arg1, arg2]
        assert original_argv == ["agdt-show", "arg1", "arg2"]

    def test_calls_run_command_with_command_name(self):
        """Test that main calls run_command with the command name."""
        mock_func = MagicMock()
        mock_module = MagicMock()
        mock_module.show_cmd = mock_func

        with patch("importlib.import_module", return_value=mock_module):
            with patch.object(sys, "argv", ["runner", "agdt-show"]):
                runner.main()

        mock_func.assert_called_once()

    def test_handles_command_with_no_additional_args(self):
        """Test that main works when command has no additional arguments."""
        captured_argv = None

        def capture_argv():
            nonlocal captured_argv
            captured_argv = sys.argv.copy()

        mock_func = MagicMock(side_effect=capture_argv)
        mock_module = MagicMock()
        mock_module.show_cmd = mock_func

        with patch("importlib.import_module", return_value=mock_module):
            with patch.object(sys, "argv", ["runner", "agdt-show"]):
                runner.main()

        assert captured_argv == ["agdt-show"]
