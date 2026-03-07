"""Tests for ensure_default_config function."""

import json

from agentic_devtools.cli.azure_devops.review_models_config import (
    _DEFAULT_BOSS_MODEL,
    _DEFAULT_REVIEWER_MODELS,
    ensure_default_config,
)


class TestEnsureDefaultConfig:
    """Tests for ensure_default_config."""

    def test_creates_config_when_absent(self, tmp_path):
        """Creates the default config file when it does not exist."""
        result = ensure_default_config(str(tmp_path))
        assert result.exists()
        data = json.loads(result.read_text())
        assert data["reviewerModels"] == list(_DEFAULT_REVIEWER_MODELS)
        assert data["bossModel"] == _DEFAULT_BOSS_MODEL

    def test_overwrites_existing_base(self, tmp_path):
        """Overwrites existing base config with current defaults."""
        config_dir = tmp_path / ".agdt" / "config"
        config_dir.mkdir(parents=True)
        old_data = {"reviewerModels": ["Old Model"], "bossModel": "Old Model"}
        base_path = config_dir / "review-models.json"
        base_path.write_text(json.dumps(old_data))

        result = ensure_default_config(str(tmp_path))
        data = json.loads(result.read_text())
        assert data["reviewerModels"] == list(_DEFAULT_REVIEWER_MODELS)

    def test_creates_directory_structure(self, tmp_path):
        """Creates .agdt/config/ directory if it does not exist."""
        result = ensure_default_config(str(tmp_path))
        assert result.parent.name == "config"
        assert result.parent.parent.name == ".agdt"

    def test_does_not_touch_override_file(self, tmp_path):
        """Does not create or modify override files."""
        config_dir = tmp_path / ".agdt" / "config"
        config_dir.mkdir(parents=True)
        override_path = config_dir / "review-models-override.json"
        override_data = {"reviewerModels": ["Custom"], "bossModel": "Custom"}
        override_path.write_text(json.dumps(override_data))

        ensure_default_config(str(tmp_path))

        # Override file should be untouched
        assert json.loads(override_path.read_text()) == override_data
