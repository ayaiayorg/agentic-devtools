"""Tests for is_gh_copilot_available."""

import subprocess
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.copilot import session as session_module
from agentic_devtools.cli.copilot.session import is_gh_copilot_available


class TestIsGhCopilotAvailable:
    """Tests for is_gh_copilot_available."""

    def test_returns_false_when_gh_not_on_path(self):
        """Returns False when the gh binary is not found on PATH."""
        with patch("agentic_devtools.cli.copilot.session.shutil.which", return_value=None):
            assert is_gh_copilot_available() is False

    def test_returns_false_when_copilot_extension_not_installed(self):
        """Returns False when gh is present but copilot extension exits non-zero."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        with patch("agentic_devtools.cli.copilot.session.shutil.which", return_value="/usr/bin/gh"):
            with patch.object(session_module, "run_safe", return_value=mock_result):
                assert is_gh_copilot_available() is False

    def test_returns_true_when_both_checks_pass(self):
        """Returns True when gh is found and copilot --help exits 0."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("agentic_devtools.cli.copilot.session.shutil.which", return_value="/usr/bin/gh"):
            with patch.object(session_module, "run_safe", return_value=mock_result):
                assert is_gh_copilot_available() is True

    def test_run_safe_called_with_shell_false(self):
        """run_safe is called with shell=False to prevent env-var expansion on Windows."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("agentic_devtools.cli.copilot.session.shutil.which", return_value="/usr/bin/gh"):
            with patch.object(session_module, "run_safe", return_value=mock_result) as mock_run:
                is_gh_copilot_available()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs.get("shell") is False

    def test_returns_false_on_oserror(self):
        """Returns False when run_safe raises OSError."""
        with patch("agentic_devtools.cli.copilot.session.shutil.which", return_value="/usr/bin/gh"):
            with patch.object(session_module, "run_safe", side_effect=OSError("not found")):
                assert is_gh_copilot_available() is False

    def test_returns_false_on_timeout(self):
        """Returns False when run_safe raises TimeoutExpired."""
        with patch("agentic_devtools.cli.copilot.session.shutil.which", return_value="/usr/bin/gh"):
            with patch.object(
                session_module,
                "run_safe",
                side_effect=subprocess.TimeoutExpired(cmd=[], timeout=10),
            ):
                assert is_gh_copilot_available() is False
