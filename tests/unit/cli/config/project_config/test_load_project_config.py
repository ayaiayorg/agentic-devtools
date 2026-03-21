"""Tests for load_project_config function."""

import json
from unittest.mock import patch

from agentic_devtools.cli.config.project_config import load_project_config


class TestLoadProjectConfig:
    """Tests for load_project_config function."""

    @patch("agentic_devtools.cli.config.project_config._get_config_path", return_value=None)
    def test_returns_empty_dict_when_not_in_git_repo(self, _mock_path):
        """Should return empty dict when not in a git repo."""
        result = load_project_config()
        assert result == {}

    def test_returns_empty_dict_when_file_missing(self, tmp_path):
        """Should return empty dict when config file does not exist."""
        missing = tmp_path / "nonexistent" / "project.json"
        with patch("agentic_devtools.cli.config.project_config._get_config_path", return_value=missing):
            result = load_project_config()
        assert result == {}

    def test_returns_parsed_json(self, tmp_path):
        """Should return parsed JSON from config file."""
        config_file = tmp_path / "project.json"
        config_file.write_text(json.dumps({"jira_project_keys": "DFLY,PROJ"}), encoding="utf-8")
        with patch("agentic_devtools.cli.config.project_config._get_config_path", return_value=config_file):
            result = load_project_config()
        assert result == {"jira_project_keys": "DFLY,PROJ"}

    def test_returns_empty_dict_on_malformed_json(self, tmp_path, capsys):
        """Should return empty dict and warn on malformed JSON."""
        config_file = tmp_path / "project.json"
        config_file.write_text("{bad json", encoding="utf-8")
        with patch("agentic_devtools.cli.config.project_config._get_config_path", return_value=config_file):
            result = load_project_config()
        assert result == {}
        captured = capsys.readouterr()
        assert "Malformed JSON" in captured.err

    def test_returns_empty_dict_on_non_dict_json(self, tmp_path, capsys):
        """Should return empty dict and warn when JSON root is not an object."""
        config_file = tmp_path / "project.json"
        config_file.write_text('["a", "b"]', encoding="utf-8")
        with patch("agentic_devtools.cli.config.project_config._get_config_path", return_value=config_file):
            result = load_project_config()
        assert result == {}
        captured = capsys.readouterr()
        assert "Expected JSON object" in captured.err

    def test_returns_empty_dict_on_read_error(self, tmp_path, capsys):
        """Should return empty dict and warn on I/O read error."""
        config_file = tmp_path / "project.json"
        config_file.mkdir()  # directory, not a file — will cause OSError on read_text
        with patch("agentic_devtools.cli.config.project_config._get_config_path", return_value=config_file):
            result = load_project_config()
        assert result == {}
        captured = capsys.readouterr()
        assert "Cannot read" in captured.err
