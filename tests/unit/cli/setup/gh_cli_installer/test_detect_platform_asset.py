"""Tests for detect_platform_asset (gh_cli_installer)."""

import platform
from unittest.mock import patch

import pytest

from agentic_devtools.cli.setup import gh_cli_installer

_ASSETS = [
    {"name": "gh_2.65.0_linux_amd64.tar.gz"},
    {"name": "gh_2.65.0_linux_arm64.tar.gz"},
    {"name": "gh_2.65.0_macOS_amd64.zip"},
    {"name": "gh_2.65.0_macOS_arm64.zip"},
    {"name": "gh_2.65.0_windows_amd64.zip"},
    # checksums and other assets that should be ignored
    {"name": "gh_2.65.0_checksums.txt"},
]


class TestDetectPlatformAssetGh:
    """Tests for detect_platform_asset in gh_cli_installer."""

    def test_linux_amd64(self):
        """Selects the Linux amd64 tarball on Linux x86_64."""
        with patch.object(platform, "system", return_value="Linux"):
            with patch.object(platform, "machine", return_value="x86_64"):
                result = gh_cli_installer.detect_platform_asset(_ASSETS)
        assert result == "gh_2.65.0_linux_amd64.tar.gz"

    def test_linux_arm64(self):
        """Selects the Linux arm64 tarball on Linux aarch64."""
        with patch.object(platform, "system", return_value="Linux"):
            with patch.object(platform, "machine", return_value="aarch64"):
                result = gh_cli_installer.detect_platform_asset(_ASSETS)
        assert result == "gh_2.65.0_linux_arm64.tar.gz"

    def test_macos_arm64(self):
        """Selects the macOS arm64 zip on Darwin arm64."""
        with patch.object(platform, "system", return_value="Darwin"):
            with patch.object(platform, "machine", return_value="arm64"):
                result = gh_cli_installer.detect_platform_asset(_ASSETS)
        assert result == "gh_2.65.0_macOS_arm64.zip"

    def test_macos_amd64(self):
        """Selects the macOS amd64 zip on Darwin x86_64."""
        with patch.object(platform, "system", return_value="Darwin"):
            with patch.object(platform, "machine", return_value="x86_64"):
                result = gh_cli_installer.detect_platform_asset(_ASSETS)
        assert result == "gh_2.65.0_macOS_amd64.zip"

    def test_windows_amd64(self):
        """Selects the Windows amd64 zip on Windows x86_64."""
        with patch.object(platform, "system", return_value="Windows"):
            with patch.object(platform, "machine", return_value="x86_64"):
                result = gh_cli_installer.detect_platform_asset(_ASSETS)
        assert result == "gh_2.65.0_windows_amd64.zip"

    def test_raises_on_unsupported_arch(self):
        """Raises RuntimeError for unsupported architecture."""
        with patch.object(platform, "system", return_value="Linux"):
            with patch.object(platform, "machine", return_value="mips"):
                with pytest.raises(RuntimeError, match="Unsupported architecture"):
                    gh_cli_installer.detect_platform_asset(_ASSETS)

    def test_raises_on_unsupported_os(self):
        """Raises RuntimeError for unsupported operating system."""
        with patch.object(platform, "system", return_value="FreeBSD"):
            with patch.object(platform, "machine", return_value="x86_64"):
                with pytest.raises(RuntimeError, match="Unsupported operating system"):
                    gh_cli_installer.detect_platform_asset(_ASSETS)

    def test_raises_when_asset_not_found(self):
        """Raises RuntimeError when no matching asset exists."""
        assets = [{"name": "gh_2.65.0_checksums.txt"}]
        with patch.object(platform, "system", return_value="Linux"):
            with patch.object(platform, "machine", return_value="x86_64"):
                with pytest.raises(RuntimeError, match="No release asset found"):
                    gh_cli_installer.detect_platform_asset(assets)

    def test_arm64_alias(self):
        """arm64 machine string is treated as arm64."""
        with patch.object(platform, "system", return_value="Linux"):
            with patch.object(platform, "machine", return_value="arm64"):
                result = gh_cli_installer.detect_platform_asset(_ASSETS)
        assert result == "gh_2.65.0_linux_arm64.tar.gz"
