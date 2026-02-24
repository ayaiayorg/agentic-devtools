"""Tests for agentic_devtools.config.load_repo_config."""

import json
import logging
from pathlib import Path
from unittest.mock import patch

from agentic_devtools.config import load_repo_config


class TestLoadRepoConfig:
    """Tests for load_repo_config function."""

    def test_returns_empty_dict_when_config_file_missing(self, tmp_path):
        """Return {} when .github/agdt-config.json does not exist."""
        result = load_repo_config(str(tmp_path))
        assert result == {}

    def test_returns_parsed_config_when_file_exists(self, tmp_path):
        """Return parsed dict when config file is valid JSON."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        config = {"review": {"focus-areas-file": ".github/review-focus-areas.md"}}
        (github_dir / "agdt-config.json").write_text(json.dumps(config), encoding="utf-8")

        result = load_repo_config(str(tmp_path))

        assert result == config

    def test_returns_empty_dict_for_invalid_json(self, tmp_path):
        """Return {} and log a warning when the file contains invalid JSON."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        (github_dir / "agdt-config.json").write_text("{ not valid json", encoding="utf-8")

        result = load_repo_config(str(tmp_path))

        assert result == {}

    def test_returns_empty_dict_for_empty_review_section(self, tmp_path):
        """Return config with empty review section when no focus-areas-file key."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        config = {"review": {}}
        (github_dir / "agdt-config.json").write_text(json.dumps(config), encoding="utf-8")

        result = load_repo_config(str(tmp_path))

        assert result == {"review": {}}

    def test_returns_full_config_with_extra_keys(self, tmp_path):
        """Preserve unrecognised top-level keys (future extensibility)."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        config = {
            "review": {"focus-areas-file": ".github/focus.md"},
            "other-section": {"key": "value"},
        }
        (github_dir / "agdt-config.json").write_text(json.dumps(config), encoding="utf-8")

        result = load_repo_config(str(tmp_path))

        assert result == config

    def test_logs_warning_for_invalid_json(self, tmp_path, caplog):
        """A warning is logged when the config contains invalid JSON."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        (github_dir / "agdt-config.json").write_text("{ bad", encoding="utf-8")

        with caplog.at_level(logging.WARNING, logger="agentic_devtools.config"):
            load_repo_config(str(tmp_path))

        assert any("Invalid JSON" in record.message for record in caplog.records)

    def test_accepts_path_object_as_string(self, tmp_path):
        """str(Path) is accepted as repo_path — just exercises the str() path."""
        result = load_repo_config(str(tmp_path))
        assert result == {}

    def test_returns_empty_dict_and_logs_warning_on_oserror(self, tmp_path, caplog):
        """Return {} and log a warning when reading the config file raises OSError."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        (github_dir / "agdt-config.json").write_text("{}", encoding="utf-8")

        with patch.object(Path, "read_text", side_effect=OSError("I/O error")):
            with caplog.at_level(logging.WARNING, logger="agentic_devtools.config"):
                result = load_repo_config(str(tmp_path))

        assert result == {}
        assert any(record.levelno == logging.WARNING for record in caplog.records)

    def test_returns_empty_dict_when_json_is_not_an_object(self, tmp_path, caplog):
        """Return {} and log a warning when config JSON root is not an object."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()

        for non_object in ["[]", '"a string"', "42", "true", "null"]:
            (github_dir / "agdt-config.json").write_text(non_object, encoding="utf-8")
            caplog.clear()
            with caplog.at_level(logging.WARNING, logger="agentic_devtools.config"):
                result = load_repo_config(str(tmp_path))
            assert result == {}, f"expected {{}} for JSON input {non_object!r}"
            assert any("Expected a JSON object" in record.message for record in caplog.records), (
                f"expected warning for JSON input {non_object!r}"
            )
