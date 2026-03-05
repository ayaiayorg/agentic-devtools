"""Tests for detect_shell_type."""

from unittest.mock import patch

from agentic_devtools.cli.setup.shell_profile import detect_shell_type


class TestDetectShellType:
    """Tests for detect_shell_type."""

    def test_returns_bash_when_shell_is_bash(self, monkeypatch):
        """Returns 'bash' when $SHELL ends with 'bash'."""
        monkeypatch.setenv("SHELL", "/bin/bash")
        with patch("agentic_devtools.cli.setup.shell_profile.sys") as mock_sys:
            mock_sys.platform = "linux"
            assert detect_shell_type() == "bash"

    def test_returns_zsh_when_shell_is_zsh(self, monkeypatch):
        """Returns 'zsh' when $SHELL ends with 'zsh'."""
        monkeypatch.setenv("SHELL", "/usr/bin/zsh")
        with patch("agentic_devtools.cli.setup.shell_profile.sys") as mock_sys:
            mock_sys.platform = "linux"
            assert detect_shell_type() == "zsh"

    def test_returns_unknown_when_shell_is_fish(self, monkeypatch):
        """Returns 'unknown' for unsupported shells like fish."""
        monkeypatch.setenv("SHELL", "/usr/bin/fish")
        with patch("agentic_devtools.cli.setup.shell_profile.sys") as mock_sys:
            mock_sys.platform = "linux"
            assert detect_shell_type() == "unknown"

    def test_returns_unknown_when_shell_empty(self, monkeypatch):
        """Returns 'unknown' when $SHELL is empty."""
        monkeypatch.setenv("SHELL", "")
        with patch("agentic_devtools.cli.setup.shell_profile.sys") as mock_sys:
            mock_sys.platform = "linux"
            assert detect_shell_type() == "unknown"

    def test_returns_unknown_when_shell_unset(self, monkeypatch):
        """Returns 'unknown' when $SHELL is not set."""
        monkeypatch.delenv("SHELL", raising=False)
        with patch("agentic_devtools.cli.setup.shell_profile.sys") as mock_sys:
            mock_sys.platform = "linux"
            assert detect_shell_type() == "unknown"

    def test_returns_powershell_on_windows(self, monkeypatch):
        """Returns 'powershell' on Windows regardless of $SHELL."""
        with patch("agentic_devtools.cli.setup.shell_profile.sys") as mock_sys:
            mock_sys.platform = "win32"
            assert detect_shell_type() == "powershell"
