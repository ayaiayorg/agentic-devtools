"""Tests for agentic_devtools.config.save_platform_config."""

import json
import logging
from pathlib import Path
from unittest.mock import patch

from agentic_devtools.config import (
    load_platform_config,
    load_repo_config,
    save_platform_config,
)


class TestSavePlatformConfig:
    """Tests for save_platform_config function."""

    def test_creates_directory_and_file_when_neither_exists(self, tmp_path):
        """Create .github/ directory and agdt-config.json when neither exists."""
        platform_config = {"issue_adapter": "github", "code_hosting": "github"}

        result = save_platform_config(str(tmp_path), platform_config)

        assert result is True
        config_path = tmp_path / ".github" / "agdt-config.json"
        assert config_path.exists()

    def test_writes_correct_json_formatting(self, tmp_path):
        """Written file uses indent=2 JSON formatting with a trailing newline."""
        platform_config = {"issue_adapter": "jira"}

        save_platform_config(str(tmp_path), platform_config)

        config_path = tmp_path / ".github" / "agdt-config.json"
        content = config_path.read_text(encoding="utf-8")
        expected = json.dumps({"platform": {"issue_adapter": "jira"}}, indent=2) + "\n"
        assert content == expected

    def test_preserves_existing_review_section(self, tmp_path):
        """Preserve existing 'review' section when saving platform config."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        existing = {"review": {"focus-areas-file": ".github/focus.md"}}
        (github_dir / "agdt-config.json").write_text(json.dumps(existing), encoding="utf-8")

        platform_config = {"issue_adapter": "github"}
        save_platform_config(str(tmp_path), platform_config)

        saved = json.loads((github_dir / "agdt-config.json").read_text(encoding="utf-8"))
        assert saved["review"] == {"focus-areas-file": ".github/focus.md"}
        assert saved["platform"] == {"issue_adapter": "github"}

    def test_overwrites_existing_platform_section(self, tmp_path):
        """Overwrite existing 'platform' section with new values."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        existing = {"platform": {"issue_adapter": "jira", "code_hosting": "other"}}
        (github_dir / "agdt-config.json").write_text(json.dumps(existing), encoding="utf-8")

        new_platform = {"issue_adapter": "github", "code_hosting": "github"}
        save_platform_config(str(tmp_path), new_platform)

        saved = json.loads((github_dir / "agdt-config.json").read_text(encoding="utf-8"))
        assert saved["platform"] == {"issue_adapter": "github", "code_hosting": "github"}

    def test_returns_true_on_success(self, tmp_path):
        """Return True when the write succeeds."""
        result = save_platform_config(str(tmp_path), {"issue_adapter": "jira"})
        assert result is True

    def test_returns_false_and_logs_warning_on_oserror(self, tmp_path, caplog):
        """Return False and log a warning when an OSError occurs during write."""
        with patch.object(Path, "write_text", side_effect=OSError("Permission denied")):
            with caplog.at_level(logging.WARNING, logger="agentic_devtools.config"):
                result = save_platform_config(str(tmp_path), {"issue_adapter": "jira"})

        assert result is False
        assert any("Could not write" in record.message for record in caplog.records)

    def test_returns_false_and_logs_warning_for_non_dict_platform_config(self, tmp_path, caplog):
        """Return False and log a warning when platform_config is not a dict."""
        with caplog.at_level(logging.WARNING, logger="agentic_devtools.config"):
            result = save_platform_config(str(tmp_path), "not-a-dict")

        assert result is False
        assert any("Expected platform_config to be a dict" in record.message for record in caplog.records)
        # Ensure no file was written
        assert not (tmp_path / ".github" / "agdt-config.json").exists()

    def test_returns_false_and_logs_warning_on_non_serializable_value(self, tmp_path, caplog):
        """Return False and log a warning when platform_config contains non-JSON-serializable values."""
        non_serializable = {"issue_adapter": "jira", "callback": object()}
        with caplog.at_level(logging.WARNING, logger="agentic_devtools.config"):
            result = save_platform_config(str(tmp_path), non_serializable)

        assert result is False
        assert any("Could not write" in record.message for record in caplog.records)

    def test_handles_invalid_json_file_gracefully(self, tmp_path):
        """Overwrite pre-existing invalid JSON file — load_repo_config returns {}."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        (github_dir / "agdt-config.json").write_text("{ not valid json", encoding="utf-8")

        platform_config = {"issue_adapter": "markdown"}
        result = save_platform_config(str(tmp_path), platform_config)

        assert result is True
        saved = json.loads((github_dir / "agdt-config.json").read_text(encoding="utf-8"))
        assert saved == {"platform": {"issue_adapter": "markdown"}}

    def test_round_trip_save_then_load(self, tmp_path):
        """Round-trip: save_platform_config then load_platform_config returns equivalent data."""
        platform_config = {
            "issue_adapter": "github",
            "code_hosting": "github",
            "jira": {},
            "github": {"repo_owner": "org", "repo_name": "repo"},
            "azure_devops": {},
        }

        save_platform_config(str(tmp_path), platform_config)
        loaded = load_platform_config(str(tmp_path))

        assert loaded["issue_adapter"] == "github"
        assert loaded["code_hosting"] == "github"
        assert loaded["github"] == {"repo_owner": "org", "repo_name": "repo"}
        assert loaded["jira"] == {}
        assert loaded["azure_devops"] == {}


class TestBackwardCompatibility:
    """Ensure existing functions work unchanged when platform section is present."""

    def test_load_repo_config_unaffected_by_platform_section(self, tmp_path):
        """load_repo_config still returns the full config dict including platform."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        config = {
            "review": {"focus-areas-file": ".github/focus.md"},
            "platform": {"issue_adapter": "github"},
        }
        (github_dir / "agdt-config.json").write_text(json.dumps(config), encoding="utf-8")

        result = load_repo_config(str(tmp_path))

        assert result == config

    def test_load_review_focus_areas_unaffected_by_platform_section(self, tmp_path):
        """load_review_focus_areas still reads focus areas when platform section is present."""
        from agentic_devtools.config import load_review_focus_areas

        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        config = {
            "review": {"focus-areas-file": ".github/focus.md"},
            "platform": {"issue_adapter": "github"},
        }
        (github_dir / "agdt-config.json").write_text(json.dumps(config), encoding="utf-8")
        (github_dir / "focus.md").write_text("# Focus Areas\n", encoding="utf-8")

        result = load_review_focus_areas(str(tmp_path))

        assert result == "# Focus Areas\n"
