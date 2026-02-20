"""
Tests for cli/runner.py module.

This module tests the command runner that maps agdt-* commands to their
entry point functions.
"""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli import runner


class TestRunCommand:
    """Tests for the run_command function."""

    def test_exits_with_error_for_unknown_command(self):
        """Test that run_command exits with error for unknown command."""
        with pytest.raises(SystemExit) as exc_info:
            runner.run_command("unknown-command")
        assert exc_info.value.code == 1

    def test_prints_error_for_unknown_command(self, capsys):
        """Test that run_command prints error message for unknown command."""
        with pytest.raises(SystemExit):
            runner.run_command("unknown-command")
        captured = capsys.readouterr()
        assert "Unknown command: unknown-command" in captured.err
        assert "Available commands:" in captured.err

    def test_imports_and_runs_known_command(self):
        """Test that run_command imports and runs a known command."""
        mock_func = MagicMock()
        mock_module = MagicMock()
        mock_module.show_cmd = mock_func

        with patch("importlib.import_module", return_value=mock_module):
            runner.run_command("agdt-show")

        mock_func.assert_called_once()

    def test_exits_on_import_error(self):
        """Test that run_command exits on import error."""
        with patch("importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("Module not found")
            with pytest.raises(SystemExit) as exc_info:
                runner.run_command("agdt-show")
        assert exc_info.value.code == 1

    def test_exits_on_attribute_error(self):
        """Test that run_command exits when function not found in module."""
        mock_module = MagicMock(spec=[])  # Module without the expected attribute
        delattr(mock_module, "show_cmd") if hasattr(mock_module, "show_cmd") else None

        with patch("importlib.import_module", return_value=mock_module):
            with pytest.raises(SystemExit) as exc_info:
                runner.run_command("agdt-show")
        assert exc_info.value.code == 1

    def test_prints_error_message_on_import_error(self, capsys):
        """Test that run_command prints error message on import error."""
        with patch("importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("Module not found")
            with pytest.raises(SystemExit):
                runner.run_command("agdt-show")
        captured = capsys.readouterr()
        assert "Error loading command agdt-show" in captured.err
