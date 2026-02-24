"""Tests for agentic_devtools.config.load_review_focus_areas."""

import json
import logging

from agentic_devtools.config import load_review_focus_areas


class TestLoadReviewFocusAreas:
    """Tests for load_review_focus_areas function."""

    def test_returns_none_when_config_file_missing(self, tmp_path):
        """Return None when .github/agdt-config.json does not exist."""
        result = load_review_focus_areas(str(tmp_path))
        assert result is None

    def test_returns_none_when_review_section_missing(self, tmp_path):
        """Return None when config has no 'review' key."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        (github_dir / "agdt-config.json").write_text(json.dumps({}), encoding="utf-8")

        result = load_review_focus_areas(str(tmp_path))

        assert result is None

    def test_returns_none_when_focus_areas_file_key_missing(self, tmp_path):
        """Return None when 'review' section exists but has no focus-areas-file."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        config = {"review": {}}
        (github_dir / "agdt-config.json").write_text(json.dumps(config), encoding="utf-8")

        result = load_review_focus_areas(str(tmp_path))

        assert result is None

    def test_returns_markdown_content_when_all_present(self, tmp_path):
        """Return raw markdown when config and focus areas file both exist."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        config = {"review": {"focus-areas-file": ".github/review-focus-areas.md"}}
        (github_dir / "agdt-config.json").write_text(json.dumps(config), encoding="utf-8")

        markdown = "## Focus Areas\n\n- Check DI registration\n"
        (github_dir / "review-focus-areas.md").write_text(markdown, encoding="utf-8")

        result = load_review_focus_areas(str(tmp_path))

        assert result == markdown

    def test_returns_none_when_focus_areas_file_missing(self, tmp_path):
        """Return None (not an error) when referenced focus-areas-file is absent."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        config = {"review": {"focus-areas-file": ".github/nonexistent.md"}}
        (github_dir / "agdt-config.json").write_text(json.dumps(config), encoding="utf-8")

        result = load_review_focus_areas(str(tmp_path))

        assert result is None

    def test_logs_warning_when_focus_areas_file_missing(self, tmp_path, caplog):
        """A warning is logged when the referenced focus-areas-file does not exist."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        config = {"review": {"focus-areas-file": ".github/nonexistent.md"}}
        (github_dir / "agdt-config.json").write_text(json.dumps(config), encoding="utf-8")

        with caplog.at_level(logging.WARNING, logger="agentic_devtools.config"):
            load_review_focus_areas(str(tmp_path))

        assert any("focus-areas-file not found" in record.message for record in caplog.records)

    def test_focus_areas_file_relative_to_repo_root(self, tmp_path):
        """The focus-areas-file path is resolved relative to repo_path, not cwd."""
        subdir = tmp_path / "docs"
        subdir.mkdir()
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        config = {"review": {"focus-areas-file": "docs/focus.md"}}
        (github_dir / "agdt-config.json").write_text(json.dumps(config), encoding="utf-8")
        (subdir / "focus.md").write_text("# Focus", encoding="utf-8")

        result = load_review_focus_areas(str(tmp_path))

        assert result == "# Focus"

    def test_returns_none_when_config_invalid_json(self, tmp_path):
        """Return None (gracefully) when config JSON is invalid."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        (github_dir / "agdt-config.json").write_text("{ bad json", encoding="utf-8")

        result = load_review_focus_areas(str(tmp_path))

        assert result is None
