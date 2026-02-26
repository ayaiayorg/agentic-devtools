"""Tests for get_installed_version (copilot_cli_installer)."""

import json
from unittest.mock import patch

from agentic_devtools.cli.setup import copilot_cli_installer


class TestGetInstalledVersionCopilot:
    """Tests for get_installed_version in copilot_cli_installer."""

    def test_returns_none_when_version_file_absent(self, tmp_path):
        """Returns None when the version tracking file does not exist."""
        version_file = tmp_path / "copilot-cli-version.json"
        with patch.object(copilot_cli_installer, "_VERSION_FILE", version_file):
            result = copilot_cli_installer.get_installed_version()
        assert result is None

    def test_returns_version_string_from_file(self, tmp_path):
        """Returns the version string stored in the JSON file."""
        version_file = tmp_path / "copilot-cli-version.json"
        version_file.write_text(
            json.dumps({"version": "v0.0.419", "installed_at": "2024-01-01T00:00:00Z"}),
            encoding="utf-8",
        )
        with patch.object(copilot_cli_installer, "_VERSION_FILE", version_file):
            result = copilot_cli_installer.get_installed_version()
        assert result == "v0.0.419"

    def test_returns_none_on_invalid_json(self, tmp_path):
        """Returns None when the version file contains invalid JSON."""
        version_file = tmp_path / "copilot-cli-version.json"
        version_file.write_text("not-json", encoding="utf-8")
        with patch.object(copilot_cli_installer, "_VERSION_FILE", version_file):
            result = copilot_cli_installer.get_installed_version()
        assert result is None

    def test_returns_none_when_version_key_missing(self, tmp_path):
        """Returns None when JSON is valid but has no 'version' key."""
        version_file = tmp_path / "copilot-cli-version.json"
        version_file.write_text(json.dumps({"asset": "copilot-linux-amd64"}), encoding="utf-8")
        with patch.object(copilot_cli_installer, "_VERSION_FILE", version_file):
            result = copilot_cli_installer.get_installed_version()
        assert result is None
