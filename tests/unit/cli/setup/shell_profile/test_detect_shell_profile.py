"""Tests for detect_shell_profile."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.setup.shell_profile import detect_shell_profile


class TestDetectShellProfile:
    """Tests for detect_shell_profile."""

    def test_returns_bashrc_when_shell_is_bash(self, monkeypatch):
        """Returns ~/.bashrc when $SHELL is /bin/bash."""
        monkeypatch.setenv("SHELL", "/bin/bash")
        with patch("agentic_devtools.cli.setup.shell_profile.sys") as mock_sys:
            mock_sys.platform = "linux"
            result = detect_shell_profile()
        assert result == Path.home() / ".bashrc"

    def test_returns_zshrc_when_shell_is_zsh(self, monkeypatch):
        """Returns ~/.zshrc when $SHELL is /usr/bin/zsh."""
        monkeypatch.setenv("SHELL", "/usr/bin/zsh")
        with patch("agentic_devtools.cli.setup.shell_profile.sys") as mock_sys:
            mock_sys.platform = "linux"
            result = detect_shell_profile()
        assert result == Path.home() / ".zshrc"

    def test_returns_none_when_shell_is_fish(self, monkeypatch):
        """Returns None for unsupported shells like fish."""
        monkeypatch.setenv("SHELL", "/usr/bin/fish")
        with patch("agentic_devtools.cli.setup.shell_profile.sys") as mock_sys:
            mock_sys.platform = "linux"
            result = detect_shell_profile()
        assert result is None

    def test_returns_none_when_shell_empty(self, monkeypatch):
        """Returns None when $SHELL is empty."""
        monkeypatch.setenv("SHELL", "")
        with patch("agentic_devtools.cli.setup.shell_profile.sys") as mock_sys:
            mock_sys.platform = "linux"
            result = detect_shell_profile()
        assert result is None

    def test_returns_none_when_shell_unset(self, monkeypatch):
        """Returns None when $SHELL is not set."""
        monkeypatch.delenv("SHELL", raising=False)
        with patch("agentic_devtools.cli.setup.shell_profile.sys") as mock_sys:
            mock_sys.platform = "linux"
            result = detect_shell_profile()
        assert result is None

    def test_returns_powershell_profile_on_windows(self, monkeypatch, tmp_path):
        """Returns PowerShell profile path on Windows when the directory exists."""
        ps_dir = tmp_path / "Documents" / "PowerShell"
        ps_dir.mkdir(parents=True)
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        with patch("agentic_devtools.cli.setup.shell_profile.sys") as mock_sys:
            mock_sys.platform = "win32"
            result = detect_shell_profile()
        assert result == ps_dir / "Microsoft.PowerShell_profile.ps1"

    def test_returns_windows_powershell_fallback(self, monkeypatch, tmp_path):
        """Falls back to WindowsPowerShell directory when PowerShell Core dir doesn't exist."""
        ps_legacy_dir = tmp_path / "Documents" / "WindowsPowerShell"
        ps_legacy_dir.mkdir(parents=True)
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        with patch("agentic_devtools.cli.setup.shell_profile.sys") as mock_sys:
            mock_sys.platform = "win32"
            result = detect_shell_profile()
        assert result == ps_legacy_dir / "Microsoft.PowerShell_profile.ps1"

    def test_returns_none_on_windows_when_no_ps_dir(self, monkeypatch, tmp_path):
        """Returns None on Windows when neither PowerShell directory exists."""
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        with patch("agentic_devtools.cli.setup.shell_profile.sys") as mock_sys:
            mock_sys.platform = "win32"
            result = detect_shell_profile()
        assert result is None

    def test_returns_none_on_windows_when_userprofile_empty(self, monkeypatch):
        """Returns None on Windows when USERPROFILE is empty."""
        monkeypatch.setenv("USERPROFILE", "")
        with patch("agentic_devtools.cli.setup.shell_profile.sys") as mock_sys:
            mock_sys.platform = "win32"
            result = detect_shell_profile()
        assert result is None
