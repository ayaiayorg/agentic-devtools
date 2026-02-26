"""Tests for get_copilot_cli_binary."""

import shutil
from unittest.mock import patch

from agentic_devtools.cli.setup import copilot_cli_installer


class TestGetCopilotCliBinary:
    """Tests for get_copilot_cli_binary."""

    def test_returns_managed_binary_when_present(self, tmp_path):
        """Returns path to managed binary when it exists in ~/.agdt/bin/."""
        managed = tmp_path / "copilot"
        managed.touch()
        with patch.object(copilot_cli_installer, "_INSTALL_DIR", tmp_path):
            result = copilot_cli_installer.get_copilot_cli_binary()
        assert result == str(managed)

    def test_returns_system_path_when_managed_not_present(self, tmp_path):
        """Falls back to shutil.which when managed binary is absent."""
        with patch.object(copilot_cli_installer, "_INSTALL_DIR", tmp_path):
            with patch.object(shutil, "which", return_value="/usr/bin/copilot"):
                result = copilot_cli_installer.get_copilot_cli_binary()
        assert result == "/usr/bin/copilot"

    def test_returns_none_when_not_found_anywhere(self, tmp_path):
        """Returns None when binary is neither managed nor on PATH."""
        with patch.object(copilot_cli_installer, "_INSTALL_DIR", tmp_path):
            with patch.object(shutil, "which", return_value=None):
                result = copilot_cli_installer.get_copilot_cli_binary()
        assert result is None
