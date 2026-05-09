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
        config_file.write_text(json.dumps({"jira_project_keys": "ACME,PROJ"}), encoding="utf-8")
        with patch("agentic_devtools.cli.config.project_config._get_config_path", return_value=config_file):
            result = load_project_config()
        assert result == {"jira_project_keys": "ACME,PROJ"}

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

    def test_returns_empty_dict_on_unicode_decode_error(self, tmp_path, capsys):
        """Should return empty dict and warn on non-UTF8 file."""
        config_file = tmp_path / "project.json"
        # Write raw bytes that are definitively invalid UTF-8
        config_file.write_bytes(b"\x80\x81\x82")
        with patch("agentic_devtools.cli.config.project_config._get_config_path", return_value=config_file):
            result = load_project_config()
        assert result == {}
        captured = capsys.readouterr()
        assert "Cannot read" in captured.err

    def test_explicit_git_root_reads_from_that_path(self, tmp_path):
        """When git_root is passed, reads config from that path directly."""
        config_dir = tmp_path / ".agdt" / "config"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "project.json"
        config_file.write_text(json.dumps({"agdt_version": "0.2.69"}), encoding="utf-8")

        result = load_project_config(git_root=tmp_path)
        assert result == {"agdt_version": "0.2.69"}
