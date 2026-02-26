"""Tests for detect_platform_asset (copilot_cli_installer)."""

import platform
from unittest.mock import patch

import pytest

from agentic_devtools.cli.setup import copilot_cli_installer

_LINUX_AMD64_ASSETS = [
    {"name": "copilot-linux-amd64"},
    {"name": "copilot-linux-arm64"},
    {"name": "copilot-darwin-amd64"},
    {"name": "copilot-darwin-arm64"},
    {"name": "copilot-windows-amd64.exe"},
]


class TestDetectPlatformAssetCopilot:
    """Tests for detect_platform_asset in copilot_cli_installer."""

    def test_linux_amd64(self):
        """Selects copilot-linux-amd64 on Linux x86_64."""
        with patch.object(platform, "system", return_value="Linux"):
            with patch.object(platform, "machine", return_value="x86_64"):
                result = copilot_cli_installer.detect_platform_asset(_LINUX_AMD64_ASSETS)
        assert result == "copilot-linux-amd64"

    def test_linux_aarch64(self):
        """Selects copilot-linux-arm64 on Linux aarch64."""
        with patch.object(platform, "system", return_value="Linux"):
            with patch.object(platform, "machine", return_value="aarch64"):
                result = copilot_cli_installer.detect_platform_asset(_LINUX_AMD64_ASSETS)
        assert result == "copilot-linux-arm64"

    def test_linux_arm64_alias(self):
        """Selects copilot-linux-arm64 on Linux arm64."""
        with patch.object(platform, "system", return_value="Linux"):
            with patch.object(platform, "machine", return_value="arm64"):
                result = copilot_cli_installer.detect_platform_asset(_LINUX_AMD64_ASSETS)
        assert result == "copilot-linux-arm64"

    def test_darwin_arm64(self):
        """Selects copilot-darwin-arm64 on macOS arm64."""
        with patch.object(platform, "system", return_value="Darwin"):
            with patch.object(platform, "machine", return_value="arm64"):
                result = copilot_cli_installer.detect_platform_asset(_LINUX_AMD64_ASSETS)
        assert result == "copilot-darwin-arm64"

    def test_windows_amd64(self):
        """Selects copilot-windows-amd64.exe on Windows x86_64."""
        with patch.object(platform, "system", return_value="Windows"):
            with patch.object(platform, "machine", return_value="x86_64"):
                result = copilot_cli_installer.detect_platform_asset(_LINUX_AMD64_ASSETS)
        assert result == "copilot-windows-amd64.exe"

    def test_raises_on_unsupported_arch(self):
        """Raises RuntimeError for unsupported architecture."""
        with patch.object(platform, "system", return_value="Linux"):
            with patch.object(platform, "machine", return_value="mips"):
                with pytest.raises(RuntimeError, match="Unsupported architecture"):
                    copilot_cli_installer.detect_platform_asset(_LINUX_AMD64_ASSETS)

    def test_raises_on_unsupported_os(self):
        """Raises RuntimeError for unsupported operating system."""
        with patch.object(platform, "system", return_value="FreeBSD"):
            with patch.object(platform, "machine", return_value="x86_64"):
                with pytest.raises(RuntimeError, match="Unsupported operating system"):
                    copilot_cli_installer.detect_platform_asset(_LINUX_AMD64_ASSETS)

    def test_raises_when_asset_not_found(self):
        """Raises RuntimeError when no matching asset exists in the list."""
        assets = [{"name": "copilot-linux-amd64"}]
        with patch.object(platform, "system", return_value="Darwin"):
            with patch.object(platform, "machine", return_value="x86_64"):
                with pytest.raises(RuntimeError, match="No release asset found"):
                    copilot_cli_installer.detect_platform_asset(assets)

    def test_amd64_alias(self):
        """amd64 machine string is treated as amd64."""
        with patch.object(platform, "system", return_value="Linux"):
            with patch.object(platform, "machine", return_value="amd64"):
                result = copilot_cli_installer.detect_platform_asset(_LINUX_AMD64_ASSETS)
        assert result == "copilot-linux-amd64"
