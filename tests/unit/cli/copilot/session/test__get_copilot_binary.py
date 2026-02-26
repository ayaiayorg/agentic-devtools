"""Tests for _get_copilot_binary."""

from unittest.mock import patch

from agentic_devtools.cli.copilot import session as session_module
from agentic_devtools.cli.copilot.session import _get_copilot_binary


class TestGetCopilotBinary:
    """Tests for _get_copilot_binary."""

    def test_returns_system_path_when_copilot_on_path(self):
        """Returns system PATH result when copilot is found via shutil.which."""
        with patch.object(session_module.shutil, "which", return_value="/usr/bin/copilot"):
            result = _get_copilot_binary()
        assert result == "/usr/bin/copilot"

    def test_returns_managed_binary_when_not_on_system_path(self, tmp_path):
        """Returns managed binary path when copilot is in ~/.agdt/bin/."""
        managed = tmp_path / "copilot"
        managed.touch()
        with patch.object(session_module.shutil, "which", return_value=None):
            with patch.object(session_module, "_MANAGED_COPILOT", managed):
                result = _get_copilot_binary()
        assert result == str(managed)

    def test_returns_none_when_not_found_anywhere(self, tmp_path):
        """Returns None when copilot is neither on PATH nor in managed location."""
        absent = tmp_path / "copilot"
        with patch.object(session_module.shutil, "which", return_value=None):
            with patch.object(session_module, "_MANAGED_COPILOT", absent):
                result = _get_copilot_binary()
        assert result is None
