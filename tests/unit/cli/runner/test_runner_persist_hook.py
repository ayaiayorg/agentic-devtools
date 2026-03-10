"""Tests for the persist_if_dirty hook integration in the CLI runner."""

import importlib
from unittest.mock import MagicMock, patch

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


class TestRunnerPersistHook:
    """Tests for persist_if_dirty being called after commands in run_command."""

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
