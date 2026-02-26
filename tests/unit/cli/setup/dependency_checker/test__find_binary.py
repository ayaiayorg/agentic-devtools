"""Tests for _find_binary (dependency_checker)."""

import shutil
from unittest.mock import patch

from agentic_devtools.cli.setup import dependency_checker
from agentic_devtools.cli.setup.dependency_checker import _find_binary


class TestFindBinary:
    """Tests for _find_binary."""

    def test_returns_managed_binary_when_present(self, tmp_path):
        """Returns managed binary path when it exists in ~/.agdt/bin/."""
        managed = tmp_path / "git"
        managed.touch()
        with patch.object(dependency_checker, "_MANAGED_BIN_DIR", tmp_path):
            result = _find_binary("git")
        assert result == str(managed)

    def test_returns_system_path_when_managed_absent(self, tmp_path):
        """Falls back to shutil.which when the managed binary doesn't exist."""
        with patch.object(dependency_checker, "_MANAGED_BIN_DIR", tmp_path):
            with patch.object(shutil, "which", return_value="/usr/bin/git"):
                result = _find_binary("git")
        assert result == "/usr/bin/git"

    def test_returns_none_when_not_found_anywhere(self, tmp_path):
        """Returns None when the binary is neither managed nor on PATH."""
        with patch.object(dependency_checker, "_MANAGED_BIN_DIR", tmp_path):
            with patch.object(shutil, "which", return_value=None):
                result = _find_binary("copilot")
        assert result is None
