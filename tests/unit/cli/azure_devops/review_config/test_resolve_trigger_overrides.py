"""Tests for resolve_trigger_overrides function."""

from agentic_devtools.cli.azure_devops.review_config import (
    ConsensusConfig,
    ReviewConfig,
    ReviewerConfig,
    TriggerConfig,
    TriggerOverride,
    resolve_trigger_overrides,
)


class TestResolveTriggerOverrides:
    """Tests for resolve_trigger_overrides."""

    def test_no_matching_trigger(self):
        """Returns unchanged config when no trigger matches the label."""
        config = ReviewConfig(
            reviewers=[
                ReviewerConfig(model_id="claude-opus-4-6", role="primary"),
                ReviewerConfig(model_id="gemini-pro-3-1", role="secondary"),
            ],
            triggers=[TriggerConfig(type="pr-label", label="ai-review")],
        )
        result = resolve_trigger_overrides(config, "other-label")
        assert len(result.reviewers) == 2
        assert result.skip_consolidation is False

    def test_skip_consolidation_override(self):
        """Applies skip_consolidation from matching trigger override."""
        config = ReviewConfig(
            reviewers=[
                ReviewerConfig(model_id="claude-opus-4-6", role="primary"),
            ],
            triggers=[
                TriggerConfig(
                    type="pr-label",
                    label="ai-review-quick",
                    override=TriggerOverride(skip_consolidation=True),
                )
            ],
        )
        result = resolve_trigger_overrides(config, "ai-review-quick")
        assert result.skip_consolidation is True

    def test_max_reviewers_override_truncates(self):
        """Applies max_reviewers override, truncating reviewer list."""
        config = ReviewConfig(
            reviewers=[
                ReviewerConfig(model_id="claude-opus-4-6", role="primary"),
                ReviewerConfig(model_id="gemini-pro-3-1", role="secondary"),
                ReviewerConfig(model_id="gpt-codex-5-3", role="tertiary"),
            ],
            consensus=ConsensusConfig(min_reviewers=1, max_reviewers=3),
            triggers=[
                TriggerConfig(
                    type="pr-label",
                    label="ai-review-quick",
                    override=TriggerOverride(max_reviewers=1),
                )
            ],
        )
        result = resolve_trigger_overrides(config, "ai-review-quick")
        assert len(result.reviewers) == 1
        assert result.reviewers[0].model_id == "claude-opus-4-6"
        assert result.consensus.max_reviewers == 1

    def test_consensus_strategy_override(self):
        """Applies consensus_strategy from matching trigger override."""
        config = ReviewConfig(
            reviewers=[
                ReviewerConfig(model_id="claude-opus-4-6", role="primary"),
            ],
            consensus=ConsensusConfig(strategy="majority"),
            triggers=[
                TriggerConfig(
                    type="pr-label",
                    label="ai-review-full",
                    override=TriggerOverride(consensus_strategy="unanimous"),
                )
            ],
        )
        result = resolve_trigger_overrides(config, "ai-review-full")
        assert result.consensus.strategy == "unanimous"

    def test_does_not_mutate_original(self):
        """resolve_trigger_overrides returns a new config, not mutated original."""
        config = ReviewConfig(
            reviewers=[
                ReviewerConfig(model_id="claude-opus-4-6", role="primary"),
                ReviewerConfig(model_id="gemini-pro-3-1", role="secondary"),
            ],
            consensus=ConsensusConfig(min_reviewers=1, max_reviewers=2),
            triggers=[
                TriggerConfig(
                    type="pr-label",
                    label="quick",
                    override=TriggerOverride(max_reviewers=1),
                )
            ],
        )
        result = resolve_trigger_overrides(config, "quick")
        assert len(config.reviewers) == 2
        assert len(result.reviewers) == 1

    def test_skip_consolidation_false_override_re_enables(self):
        """Override with skip_consolidation=False re-enables consolidation."""
        config = ReviewConfig(
            reviewers=[
                ReviewerConfig(model_id="claude-opus-4-6", role="primary"),
            ],
            skip_consolidation=True,
            triggers=[
                TriggerConfig(
                    type="pr-label",
                    label="ai-review-full",
                    override=TriggerOverride(skip_consolidation=False),
                )
            ],
        )
        result = resolve_trigger_overrides(config, "ai-review-full")
        assert result.skip_consolidation is False

    def test_combined_overrides(self):
        """Multiple override fields are all applied."""
        config = ReviewConfig(
            reviewers=[
                ReviewerConfig(model_id="claude-opus-4-6", role="primary"),
                ReviewerConfig(model_id="gemini-pro-3-1", role="secondary"),
            ],
            consensus=ConsensusConfig(strategy="majority", min_reviewers=1, max_reviewers=3),
            triggers=[
                TriggerConfig(
                    type="pr-label",
                    label="custom",
                    override=TriggerOverride(
                        max_reviewers=1,
                        skip_consolidation=True,
                        consensus_strategy="first-reviewer-wins",
                    ),
                )
            ],
        )
        result = resolve_trigger_overrides(config, "custom")
        assert len(result.reviewers) == 1
        assert result.skip_consolidation is True
        assert result.consensus.strategy == "first-reviewer-wins"
        assert result.consensus.max_reviewers == 1

    def test_clamps_min_reviewers_when_override_reduces_max(self):
        """Clamps min_reviewers to max_reviewers when override reduces below base min."""
        config = ReviewConfig(
            reviewers=[
                ReviewerConfig(model_id="claude-opus-4-6", role="primary"),
                ReviewerConfig(model_id="gemini-pro-3-1", role="secondary"),
            ],
            consensus=ConsensusConfig(min_reviewers=2, max_reviewers=3),
            triggers=[
                TriggerConfig(
                    type="pr-label",
                    label="quick",
                    override=TriggerOverride(max_reviewers=1),
                )
            ],
        )
        result = resolve_trigger_overrides(config, "quick")
        assert result.consensus.max_reviewers == 1
        assert result.consensus.min_reviewers == 1
        assert len(result.reviewers) == 1

    def test_base_config_max_reviewers_caps_reviewer_list(self):
        """Enforces max_reviewers cap even when no trigger override matched."""
        config = ReviewConfig(
            reviewers=[
                ReviewerConfig(model_id="claude-opus-4-6", role="primary"),
                ReviewerConfig(model_id="gemini-pro-3-1", role="secondary"),
                ReviewerConfig(model_id="gpt-codex-5-3", role="tertiary"),
            ],
            consensus=ConsensusConfig(min_reviewers=1, max_reviewers=2),
            triggers=[TriggerConfig(type="pr-label", label="ai-review")],
        )
        result = resolve_trigger_overrides(config, "ai-review")
        assert len(result.reviewers) == 2
        assert result.reviewers[0].model_id == "claude-opus-4-6"
        assert result.reviewers[1].model_id == "gemini-pro-3-1"
