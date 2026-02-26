"""Tests for install_copilot_cli."""

from unittest.mock import patch

import requests

from agentic_devtools.cli.setup import copilot_cli_installer


def _make_release(version: str = "v1.0.0") -> dict:
    return {
        "tag_name": version,
        "assets": [
            {"name": "copilot-linux-amd64", "browser_download_url": "https://github.com/dl/copilot"},
        ],
    }


class TestInstallCopilotCli:
    """Tests for install_copilot_cli."""

    def test_skips_when_already_up_to_date(self, capsys):
        """Prints up-to-date message and returns True when version matches."""
        release = _make_release("v1.0.0")
        with patch.object(copilot_cli_installer, "get_copilot_cli_binary", return_value="/usr/bin/copilot"):
            with patch.object(copilot_cli_installer, "get_installed_version", return_value="v1.0.0"):
                with patch.object(copilot_cli_installer, "get_latest_release_info", return_value=release):
                    result = copilot_cli_installer.install_copilot_cli()
        assert result is True
        captured = capsys.readouterr()
        assert "up-to-date" in captured.out

    def test_returns_false_on_release_fetch_error(self, capsys):
        """Returns False when release info cannot be fetched."""
        with patch.object(copilot_cli_installer, "get_copilot_cli_binary", return_value=None):
            with patch.object(copilot_cli_installer, "get_installed_version", return_value=None):
                with patch.object(
                    copilot_cli_installer,
                    "get_latest_release_info",
                    side_effect=requests.ConnectionError("no network"),
                ):
                    result = copilot_cli_installer.install_copilot_cli()
        assert result is False
        assert "Failed to fetch" in capsys.readouterr().err

    def test_returns_false_on_unsupported_platform(self, capsys):
        """Returns False when no asset matches the platform."""
        release = {"tag_name": "v1.0.0", "assets": []}
        with patch.object(copilot_cli_installer, "get_copilot_cli_binary", return_value=None):
            with patch.object(copilot_cli_installer, "get_installed_version", return_value=None):
                with patch.object(copilot_cli_installer, "get_latest_release_info", return_value=release):
                    with patch.object(
                        copilot_cli_installer,
                        "detect_platform_asset",
                        side_effect=RuntimeError("No asset"),
                    ):
                        result = copilot_cli_installer.install_copilot_cli()
        assert result is False

    def test_returns_false_when_no_download_url(self, capsys):
        """Returns False when the asset has no browser_download_url."""
        release = {
            "tag_name": "v1.0.0",
            "assets": [{"name": "copilot-linux-amd64"}],
        }
        with patch.object(copilot_cli_installer, "get_copilot_cli_binary", return_value=None):
            with patch.object(copilot_cli_installer, "get_installed_version", return_value=None):
                with patch.object(copilot_cli_installer, "get_latest_release_info", return_value=release):
                    with patch.object(
                        copilot_cli_installer, "detect_platform_asset", return_value="copilot-linux-amd64"
                    ):
                        result = copilot_cli_installer.install_copilot_cli()
        assert result is False

    def test_force_reinstall_ignores_version_match(self, capsys):
        """With force=True, reinstalls even when already up-to-date."""
        release = _make_release("v1.0.0")
        with patch.object(copilot_cli_installer, "get_copilot_cli_binary", return_value="/usr/bin/copilot"):
            with patch.object(copilot_cli_installer, "get_installed_version", return_value="v1.0.0"):
                with patch.object(copilot_cli_installer, "get_latest_release_info", return_value=release):
                    with patch.object(
                        copilot_cli_installer, "detect_platform_asset", return_value="copilot-linux-amd64"
                    ):
                        with patch.object(copilot_cli_installer, "download_and_install", return_value=True) as mock_dl:
                            result = copilot_cli_installer.install_copilot_cli(force=True)
        assert result is True
        mock_dl.assert_called_once()

    def test_successful_install_prints_paths(self, capsys):
        """Prints download and install messages on success."""
        release = _make_release("v1.0.0")
        with patch.object(copilot_cli_installer, "get_copilot_cli_binary", return_value=None):
            with patch.object(copilot_cli_installer, "get_installed_version", return_value=None):
                with patch.object(copilot_cli_installer, "get_latest_release_info", return_value=release):
                    with patch.object(
                        copilot_cli_installer, "detect_platform_asset", return_value="copilot-linux-amd64"
                    ):
                        with patch.object(copilot_cli_installer, "download_and_install", return_value=True):
                            result = copilot_cli_installer.install_copilot_cli()
        assert result is True
        out = capsys.readouterr().out
        assert "Downloaded copilot" in out
        assert "Installed to" in out
