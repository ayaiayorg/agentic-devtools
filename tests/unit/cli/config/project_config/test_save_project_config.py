"""Tests for save_project_config function."""

import json
from unittest.mock import patch

import pytest

from agentic_devtools.cli.config.project_config import save_project_config


class TestSaveProjectConfig:
    """Tests for save_project_config function."""

    def test_creates_file_and_dirs(self, tmp_path):
        """Should create directories and write config file."""
        config_file = tmp_path / "config" / "project.json"
        with patch("agentic_devtools.cli.config.project_config._get_config_path", return_value=config_file):
            result = save_project_config({"jira_project_keys": "PROJ"})
        assert result == config_file
        assert config_file.exists()
        data = json.loads(config_file.read_text(encoding="utf-8"))
        assert data == {"jira_project_keys": "PROJ"}

    def test_overwrites_existing(self, tmp_path):
        """Should overwrite existing config file."""
        config_file = tmp_path / "project.json"
        config_file.write_text('{"old": true}', encoding="utf-8")
        with patch("agentic_devtools.cli.config.project_config._get_config_path", return_value=config_file):
            save_project_config({"new": True})
        data = json.loads(config_file.read_text(encoding="utf-8"))
        assert data == {"new": True}

    def test_raises_when_no_git_root(self):
        """Should raise RuntimeError when git root cannot be determined."""
        with patch("agentic_devtools.cli.config.project_config._get_config_path", return_value=None):
            with pytest.raises(RuntimeError, match="Cannot determine git repository root"):
                save_project_config({"key": "value"})

    def test_preserves_empty_string_values(self, tmp_path):
        """Should faithfully store empty string values without stripping them."""
        config_file = tmp_path / "config" / "project.json"
        with patch("agentic_devtools.cli.config.project_config._get_config_path", return_value=config_file):
            save_project_config({"jira_project_keys": "", "vpn_url": ""})
        data = json.loads(config_file.read_text(encoding="utf-8"))
        assert data["jira_project_keys"] == ""
        assert data["vpn_url"] == ""
