"""Tests for ReviewConfig dataclass and validation."""

import pytest

from agentic_devtools.cli.azure_devops.review_config import (
    ConsensusConfig,
    ConsolidationConfig,
    ReviewConfig,
    ReviewConfigError,
    ReviewerConfig,
    TriggerConfig,
    TriggerOverride,
)


class TestReviewConfig:
    """Tests for ReviewConfig dataclass."""

    def test_default_creation(self):
        """Default ReviewConfig has empty lists and default consensus."""
        config = ReviewConfig()
        assert config.version == 1
        assert config.reviewers == []
        assert config.consolidation is None
        assert config.consensus.strategy == "majority"
        assert config.triggers == []
        assert config.skip_consolidation is False

    def test_validate_valid_config(self):
        """Valid config passes validation without error."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            consolidation=ConsolidationConfig(model_id="claude-opus-4-6"),
            consensus=ConsensusConfig(strategy="majority"),
        )
        config.validate()

    def test_validate_no_reviewers(self):
        """Config with no reviewers fails validation."""
        config = ReviewConfig(reviewers=[])
        with pytest.raises(ReviewConfigError, match="at least one reviewer"):
            config.validate()

    def test_validate_bad_version(self):
        """Config with version != 1 fails validation."""
        config = ReviewConfig(
            version=2,
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
        )
        with pytest.raises(ReviewConfigError, match="version: must be 1"):
            config.validate()

    def test_validate_unknown_model(self):
        """Config with unknown model_id fails validation."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="unknown-model", role="primary")],
        )
        with pytest.raises(ReviewConfigError, match="unknown model"):
            config.validate()

    def test_validate_bad_reviewer_role(self):
        """Config with invalid reviewer role fails validation."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="boss")],
        )
        with pytest.raises(ReviewConfigError, match="role: must be one of"):
            config.validate()

    def test_validate_bad_consolidator_role(self):
        """Config with invalid consolidator role fails validation."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            consolidation=ConsolidationConfig(model_id="claude-opus-4-6", role="reviewer"),
        )
        with pytest.raises(ReviewConfigError, match="consolidation.role"):
            config.validate()

    def test_validate_bad_consensus_strategy(self):
        """Config with invalid consensus strategy fails validation."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            consensus=ConsensusConfig(strategy="invalid"),
        )
        with pytest.raises(ReviewConfigError, match="consensus.strategy"):
            config.validate()

    def test_validate_min_reviewers_below_one(self):
        """consensus.min_reviewers < 1 fails validation."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            consensus=ConsensusConfig(min_reviewers=0),
        )
        with pytest.raises(ReviewConfigError, match="min_reviewers: must be >= 1"):
            config.validate()

    def test_validate_max_less_than_min(self):
        """consensus.max_reviewers < min_reviewers fails validation."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            consensus=ConsensusConfig(min_reviewers=3, max_reviewers=1),
        )
        with pytest.raises(ReviewConfigError, match="max_reviewers: must be >= min_reviewers"):
            config.validate()

    def test_validate_consolidator_can_match_reviewer(self):
        """Consolidator model_id matching a reviewer model_id is valid."""
        config = ReviewConfig(
            reviewers=[
                ReviewerConfig(model_id="claude-opus-4-6", role="primary"),
                ReviewerConfig(model_id="gemini-pro-3-1", role="secondary"),
            ],
            consolidation=ConsolidationConfig(model_id="claude-opus-4-6"),
        )
        config.validate()

    def test_validate_bad_trigger_type(self):
        """Trigger with type != 'pr-label' fails validation."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            triggers=[TriggerConfig(type="webhook", label="ai-review")],
        )
        with pytest.raises(ReviewConfigError, match="triggers.*type: must be 'pr-label'"):
            config.validate()

    def test_validate_empty_trigger_label(self):
        """Trigger with empty label fails validation."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            triggers=[TriggerConfig(type="pr-label", label="")],
        )
        with pytest.raises(ReviewConfigError, match="label: must be non-empty"):
            config.validate()

    def test_validate_bad_override_strategy(self):
        """Override with invalid consensus_strategy fails validation."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            triggers=[
                TriggerConfig(
                    type="pr-label",
                    label="test",
                    override=TriggerOverride(consensus_strategy="invalid"),
                )
            ],
        )
        with pytest.raises(ReviewConfigError, match="override.consensus_strategy"):
            config.validate()

    def test_validate_bad_override_max_reviewers(self):
        """Override with max_reviewers < 1 fails validation."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            triggers=[
                TriggerConfig(
                    type="pr-label",
                    label="test",
                    override=TriggerOverride(max_reviewers=0),
                )
            ],
        )
        with pytest.raises(ReviewConfigError, match="override.max_reviewers: must be >= 1"):
            config.validate()

    def test_validate_multiple_errors_collected(self):
        """Validation collects multiple errors in one exception."""
        config = ReviewConfig(
            version=2,
            reviewers=[],
        )
        with pytest.raises(ReviewConfigError) as exc_info:
            config.validate()
        msg = str(exc_info.value)
        assert "version: must be 1" in msg
        assert "at least one reviewer" in msg

    def test_multi_reviewer_config(self):
        """Config with multiple reviewers validates successfully."""
        config = ReviewConfig(
            reviewers=[
                ReviewerConfig(model_id="claude-opus-4-6", role="primary"),
                ReviewerConfig(model_id="gemini-pro-3-1", role="secondary"),
                ReviewerConfig(model_id="gpt-codex-5-3", role="tertiary"),
            ],
            consolidation=ConsolidationConfig(model_id="claude-opus-4-6"),
        )
        config.validate()

    def test_validate_unknown_consolidation_model(self):
        """Unknown consolidation model_id fails validation."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            consolidation=ConsolidationConfig(model_id="unknown-model"),
        )
        with pytest.raises(ReviewConfigError, match="consolidation.model_id"):
            config.validate()
