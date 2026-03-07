"""Tests for ReviewModelsConfig dataclass."""

import pytest

from agentic_devtools.cli.azure_devops.review_models_config import (
    _DEFAULT_BOSS_MODEL,
    _DEFAULT_REVIEWER_MODELS,
    ReviewModelsConfig,
)


class TestReviewModelsConfig:
    """Tests for ReviewModelsConfig."""

    def test_default_creation(self):
        """Test creation with default values."""
        config = ReviewModelsConfig()
        assert config.reviewerModels == list(_DEFAULT_REVIEWER_MODELS)
        assert config.bossModel == _DEFAULT_BOSS_MODEL

    def test_custom_creation(self):
        """Test creation with custom values."""
        config = ReviewModelsConfig(
            reviewerModels=["Model A", "Model B"],
            bossModel="Model A",
        )
        assert config.reviewerModels == ["Model A", "Model B"]
        assert config.bossModel == "Model A"

    def test_to_dict(self):
        """Test serialization."""
        config = ReviewModelsConfig(
            reviewerModels=["Claude Opus 4.6", "Gemini Pro 3.1"],
            bossModel="Claude Opus 4.6",
        )
        d = config.to_dict()
        assert d == {
            "reviewerModels": ["Claude Opus 4.6", "Gemini Pro 3.1"],
            "bossModel": "Claude Opus 4.6",
        }

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "reviewerModels": ["Claude Opus 4.6", "Gemini Pro 3.1"],
            "bossModel": "Claude Opus 4.6",
        }
        config = ReviewModelsConfig.from_dict(data)
        assert config.reviewerModels == ["Claude Opus 4.6", "Gemini Pro 3.1"]
        assert config.bossModel == "Claude Opus 4.6"

    def test_from_dict_defaults(self):
        """Test deserialization with missing keys uses defaults."""
        config = ReviewModelsConfig.from_dict({})
        assert config.reviewerModels == list(_DEFAULT_REVIEWER_MODELS)
        assert config.bossModel == _DEFAULT_BOSS_MODEL

    def test_validate_empty_reviewer_models(self):
        """Test validation rejects empty reviewerModels."""
        with pytest.raises(ValueError, match="non-empty list"):
            ReviewModelsConfig(reviewerModels=[], bossModel="Model A").validate()

    def test_validate_non_string_reviewer(self):
        """Test validation rejects non-string reviewer model entries."""
        with pytest.raises(ValueError, match="non-empty string"):
            ReviewModelsConfig(reviewerModels=[123], bossModel="Model A").validate()

    def test_validate_blank_reviewer(self):
        """Test validation rejects blank reviewer model entries."""
        with pytest.raises(ValueError, match="non-empty string"):
            ReviewModelsConfig(reviewerModels=["  "], bossModel="Model A").validate()

    def test_validate_blank_boss_model(self):
        """Test validation rejects blank bossModel."""
        with pytest.raises(ValueError, match="non-empty string"):
            ReviewModelsConfig(reviewerModels=["Model A"], bossModel="").validate()

    def test_validate_non_string_boss_model(self):
        """Test validation rejects non-string bossModel."""
        with pytest.raises(ValueError, match="non-empty string"):
            ReviewModelsConfig(reviewerModels=["Model A"], bossModel=123).validate()

    def test_is_multi_model_single(self):
        """Test is_multi_model returns False for single model."""
        config = ReviewModelsConfig(reviewerModels=["Model A"], bossModel="Model A")
        assert config.is_multi_model is False

    def test_is_multi_model_multiple(self):
        """Test is_multi_model returns True for multiple models."""
        config = ReviewModelsConfig(
            reviewerModels=["Model A", "Model B"],
            bossModel="Model A",
        )
        assert config.is_multi_model is True

    def test_to_dict_returns_copy(self):
        """Test to_dict returns a copy of reviewerModels list."""
        config = ReviewModelsConfig(reviewerModels=["Model A"], bossModel="Model A")
        d = config.to_dict()
        d["reviewerModels"].append("Model B")
        assert config.reviewerModels == ["Model A"]

    def test_from_dict_validation_error(self):
        """Test from_dict raises ValueError on invalid data."""
        with pytest.raises(ValueError):
            ReviewModelsConfig.from_dict({"reviewerModels": [], "bossModel": "X"})

    def test_validate_non_list_reviewer_models(self):
        """Test validation rejects non-list reviewerModels."""
        with pytest.raises(ValueError, match="non-empty list"):
            ReviewModelsConfig(reviewerModels="not a list", bossModel="Model A").validate()
