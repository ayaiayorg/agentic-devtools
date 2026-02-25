"""Tests for is_gh_copilot_available."""

import subprocess
from unittest.mock import patch

from agentic_devtools.cli.copilot.session import is_gh_copilot_available


class TestIsGhCopilotAvailable:
    """Tests for is_gh_copilot_available."""

    def test_returns_false_when_gh_not_on_path(self):
        """Returns False when the gh binary is not found on PATH."""
        with patch("agentic_devtools.cli.copilot.session.shutil.which", return_value=None):
            assert is_gh_copilot_available() is False

    def test_returns_false_when_copilot_extension_not_installed(self):
        """Returns False when gh is present but copilot extension exits non-zero."""
        with patch("agentic_devtools.cli.copilot.session.shutil.which", return_value="/usr/bin/gh"):
            mock_result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="")
            with patch("subprocess.run", return_value=mock_result):
                assert is_gh_copilot_available() is False

    def test_returns_true_when_both_checks_pass(self):
        """Returns True when gh is found and copilot --help exits 0."""
        with patch("agentic_devtools.cli.copilot.session.shutil.which", return_value="/usr/bin/gh"):
            mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            with patch("subprocess.run", return_value=mock_result):
                assert is_gh_copilot_available() is True

    def test_returns_false_on_oserror(self):
        """Returns False when subprocess.run raises OSError."""
        with patch("agentic_devtools.cli.copilot.session.shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run", side_effect=OSError("not found")):
                assert is_gh_copilot_available() is False

    def test_returns_false_on_timeout(self):
        """Returns False when subprocess.run raises TimeoutExpired."""
        with patch("agentic_devtools.cli.copilot.session.shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=[], timeout=10)):
                assert is_gh_copilot_available() is False
