"""Tests for load_review_models_config function."""

import json

import pytest

from agentic_devtools.cli.azure_devops.review_models_config import (
    _DEFAULT_BOSS_MODEL,
    _DEFAULT_REVIEWER_MODELS,
    load_review_models_config,
)


class TestLoadReviewModelsConfig:
    """Tests for load_review_models_config."""

    def test_returns_defaults_when_no_files(self, tmp_path):
        """Returns default config when no config files exist."""
        config = load_review_models_config(str(tmp_path))
        assert config.reviewerModels == list(_DEFAULT_REVIEWER_MODELS)
        assert config.bossModel == _DEFAULT_BOSS_MODEL

    def test_loads_base_config(self, tmp_path):
        """Loads base config file when it exists."""
        config_dir = tmp_path / ".agdt" / "config"
        config_dir.mkdir(parents=True)
        data = {"reviewerModels": ["Model A", "Model B"], "bossModel": "Model A"}
        (config_dir / "review-models.json").write_text(json.dumps(data))

        config = load_review_models_config(str(tmp_path))
        assert config.reviewerModels == ["Model A", "Model B"]
        assert config.bossModel == "Model A"

    def test_override_takes_precedence(self, tmp_path):
        """Override file takes precedence over base file."""
        config_dir = tmp_path / ".agdt" / "config"
        config_dir.mkdir(parents=True)
        base_data = {"reviewerModels": ["Model A"], "bossModel": "Model A"}
        override_data = {"reviewerModels": ["Model X", "Model Y"], "bossModel": "Model X"}
        (config_dir / "review-models.json").write_text(json.dumps(base_data))
        (config_dir / "review-models-override.json").write_text(json.dumps(override_data))

        config = load_review_models_config(str(tmp_path))
        assert config.reviewerModels == ["Model X", "Model Y"]
        assert config.bossModel == "Model X"

    def test_invalid_json_returns_defaults(self, tmp_path):
        """Returns defaults when config file has invalid JSON."""
        config_dir = tmp_path / ".agdt" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "review-models.json").write_text("not json")

        config = load_review_models_config(str(tmp_path))
        assert config.reviewerModels == list(_DEFAULT_REVIEWER_MODELS)

    def test_non_dict_json_returns_defaults(self, tmp_path):
        """Returns defaults when config file is a JSON array instead of object."""
        config_dir = tmp_path / ".agdt" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "review-models.json").write_text(json.dumps(["not", "a", "dict"]))

        config = load_review_models_config(str(tmp_path))
        assert config.reviewerModels == list(_DEFAULT_REVIEWER_MODELS)

    def test_validation_error_propagates(self, tmp_path):
        """Raises ValueError when loaded config fails validation."""
        config_dir = tmp_path / ".agdt" / "config"
        config_dir.mkdir(parents=True)
        data = {"reviewerModels": [], "bossModel": "Model A"}
        (config_dir / "review-models.json").write_text(json.dumps(data))

        with pytest.raises(ValueError, match="non-empty list"):
            load_review_models_config(str(tmp_path))
