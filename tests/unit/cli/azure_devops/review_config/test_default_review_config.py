"""Tests for default_review_config function."""

from agentic_devtools.cli.azure_devops.review_config import default_review_config


class TestDefaultReviewConfig:
    """Tests for default_review_config."""

    def test_returns_valid_config(self):
        """Default config passes validation."""
        config = default_review_config()
        config.validate()

    def test_single_reviewer(self):
        """Default has exactly one reviewer."""
        config = default_review_config()
        assert len(config.reviewers) == 1
        assert config.reviewers[0].model_id == "claude-opus-4-6"
        assert config.reviewers[0].role == "primary"

    def test_no_consolidation(self):
        """Default has no consolidation and skip_consolidation=True."""
        config = default_review_config()
        assert config.consolidation is None
        assert config.skip_consolidation is True

    def test_default_trigger(self):
        """Default has ai-review label trigger."""
        config = default_review_config()
        assert len(config.triggers) == 1
        assert config.triggers[0].label == "ai-review"

    def test_version_is_one(self):
        """Default config version is 1."""
        config = default_review_config()
        assert config.version == 1
