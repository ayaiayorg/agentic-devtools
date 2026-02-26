"""Tests for get_installed_version (gh_cli_installer)."""

import json
from unittest.mock import patch

from agentic_devtools.cli.setup import gh_cli_installer


class TestGetInstalledVersionGh:
    """Tests for get_installed_version in gh_cli_installer."""

    def test_returns_none_when_file_absent(self, tmp_path):
        """Returns None when the version tracking file does not exist."""
        version_file = tmp_path / "gh-cli-version.json"
        with patch.object(gh_cli_installer, "_VERSION_FILE", version_file):
            result = gh_cli_installer.get_installed_version()
        assert result is None

    def test_returns_version_string(self, tmp_path):
        """Returns the version string stored in the JSON file."""
        version_file = tmp_path / "gh-cli-version.json"
        version_file.write_text(
            json.dumps({"version": "v2.65.0", "installed_at": "2024-01-01"}),
            encoding="utf-8",
        )
        with patch.object(gh_cli_installer, "_VERSION_FILE", version_file):
            result = gh_cli_installer.get_installed_version()
        assert result == "v2.65.0"

    def test_returns_none_on_invalid_json(self, tmp_path):
        """Returns None when the file contains invalid JSON."""
        version_file = tmp_path / "gh-cli-version.json"
        version_file.write_text("not-json", encoding="utf-8")
        with patch.object(gh_cli_installer, "_VERSION_FILE", version_file):
            result = gh_cli_installer.get_installed_version()
        assert result is None

    def test_returns_none_when_version_key_missing(self, tmp_path):
        """Returns None when JSON is valid but has no 'version' key."""
        version_file = tmp_path / "gh-cli-version.json"
        version_file.write_text(json.dumps({"asset": "gh_2.65.0_linux_amd64.tar.gz"}), encoding="utf-8")
        with patch.object(gh_cli_installer, "_VERSION_FILE", version_file):
            result = gh_cli_installer.get_installed_version()
        assert result is None
