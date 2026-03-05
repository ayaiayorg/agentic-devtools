"""Tests for _print_path_instructions_if_needed."""

import os
from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.setup import commands


class TestPrintPathInstructionsIfNeeded:
    """Tests for _print_path_instructions_if_needed."""

    def test_prints_instructions_when_not_in_path(self, tmp_path, capsys):
        """Prints PATH instructions when managed bin dir is absent from PATH."""
        managed_bin = str(tmp_path / "bin")
        # Ensure the managed bin is NOT in PATH
        fake_path = "/usr/bin:/usr/local/bin"
        with patch.object(commands, "_MANAGED_BIN_DIR", Path(managed_bin)):
            with patch.dict(os.environ, {"PATH": fake_path}):
                commands._print_path_instructions_if_needed()
        captured = capsys.readouterr()
        assert "PATH" in captured.out
        assert ".agdt/bin" in captured.out

    def test_no_output_when_managed_bin_already_in_path(self, tmp_path, capsys):
        """Prints nothing when managed bin dir is already in PATH."""
        managed_bin = tmp_path / "bin"
        managed_bin.mkdir()
        fake_path = f"/usr/bin:{managed_bin}"
        with patch.object(commands, "_MANAGED_BIN_DIR", managed_bin):
            with patch.dict(os.environ, {"PATH": fake_path}):
                commands._print_path_instructions_if_needed()
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_calls_persist_when_persist_env_true(self, tmp_path, capsys):
        """Calls _persist_env_vars_to_profile when persist_env=True."""
        managed_bin = str(tmp_path / "bin")
        fake_path = "/usr/bin:/usr/local/bin"
        with patch.object(commands, "_MANAGED_BIN_DIR", Path(managed_bin)):
            with patch.dict(os.environ, {"PATH": fake_path}):
                with patch.object(commands, "_persist_env_vars_to_profile") as mock_persist:
                    commands._print_path_instructions_if_needed(persist_env=True)
        mock_persist.assert_called_once()
        assert mock_persist.call_args.kwargs["path_only"] is True
