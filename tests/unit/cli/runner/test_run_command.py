"""
Tests for cli/runner.py module.

This module tests the command runner that maps agdt-* commands to their
entry point functions.
"""

import importlib
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli import runner


def _import_side_effect(mock_module):
    """Return an import side_effect that returns mock_module for the command
    module but delegates to the real importlib for all other imports."""
    real_import = importlib.import_module

    def _side_effect(name, *args, **kwargs):
        if name == "agentic_devtools.cli.state":
            return mock_module
        return real_import(name, *args, **kwargs)

    return _side_effect


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

    def test_persist_if_dirty_called_after_command(self):
        """persist_if_dirty is called after a successful command."""
        mock_func = MagicMock()
        mock_module = MagicMock()
        mock_module.show_cmd = mock_func

        with patch("importlib.import_module", side_effect=_import_side_effect(mock_module)):
            with patch("agentic_devtools.cli.git.agdt_branch.persist_if_dirty") as mock_persist:
                runner.run_command("agdt-show")

        mock_func.assert_called_once()
        mock_persist.assert_called_once()

    def test_persist_if_dirty_called_after_command_exception(self):
        """persist_if_dirty fires even when the command raises."""
        mock_func = MagicMock(side_effect=ValueError("boom"))
        mock_module = MagicMock()
        mock_module.show_cmd = mock_func

        with patch("importlib.import_module", side_effect=_import_side_effect(mock_module)):
            with patch("agentic_devtools.cli.git.agdt_branch.persist_if_dirty") as mock_persist:
                try:
                    runner.run_command("agdt-show")
                except ValueError:
                    pass

        mock_persist.assert_called_once()

    def test_persist_hook_failure_does_not_crash_runner(self):
        """Runner swallows exceptions from the persist hook."""
        mock_func = MagicMock()
        mock_module = MagicMock()
        mock_module.show_cmd = mock_func

        with patch("importlib.import_module", side_effect=_import_side_effect(mock_module)):
            with patch(
                "agentic_devtools.cli.git.agdt_branch.persist_if_dirty",
                side_effect=RuntimeError("persist exploded"),
            ):
                # Should NOT raise despite persist hook failure
                runner.run_command("agdt-show")

        mock_func.assert_called_once()

    def test_persist_hook_import_error_prints_warning(self, capsys):
        """Runner prints a warning when persist hook cannot be imported."""
        mock_func = MagicMock()
        mock_module = MagicMock()
        mock_module.show_cmd = mock_func

        # We need to make the lazy import inside run_command's finally block fail.
        # Patch sys.modules to make the module unimportable.
        import sys

        saved = sys.modules.pop("agentic_devtools.cli.git.agdt_branch", None)
        try:
            with patch.dict(sys.modules, {"agentic_devtools.cli.git.agdt_branch": None}):
                with patch("importlib.import_module", side_effect=_import_side_effect(mock_module)):
                    # Should NOT raise despite import failure
                    runner.run_command("agdt-show")
        finally:
            if saved is not None:
                sys.modules["agentic_devtools.cli.git.agdt_branch"] = saved

        mock_func.assert_called_once()
        captured = capsys.readouterr()
        assert "Warning: could not import persist_if_dirty hook" in captured.err
