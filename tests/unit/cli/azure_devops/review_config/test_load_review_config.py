"""Tests for load_review_config function."""

from unittest.mock import patch

import pytest
import yaml

from agentic_devtools.cli.azure_devops.review_config import (
    ReviewConfigError,
    load_review_config,
)


class TestLoadReviewConfig:
    """Tests for load_review_config."""

    def test_returns_defaults_when_no_config(self, tmp_path):
        """Returns default config when no .agdt/review-config.yaml exists."""
        config = load_review_config(tmp_path)
        assert len(config.reviewers) == 1
        assert config.reviewers[0].model_id == "claude-opus-4-6"
        assert config.reviewers[0].role == "primary"
        assert config.consolidation is None
        assert config.skip_consolidation is True

    def test_loads_valid_config(self, tmp_path):
        """Loads and parses a valid YAML config file."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [
                    {"model_id": "claude-opus-4-6", "role": "primary"},
                    {"model_id": "gemini-pro-3-1", "role": "secondary"},
                ],
                "consolidation": {
                    "model_id": "claude-opus-4-6",
                    "role": "consolidator",
                },
                "consensus": {
                    "strategy": "majority",
                    "min_reviewers": 2,
                    "max_reviewers": 3,
                },
                "triggers": [
                    {"type": "pr-label", "label": "ai-review"},
                ],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        config = load_review_config(tmp_path)
        assert len(config.reviewers) == 2
        assert config.reviewers[0].model_id == "claude-opus-4-6"
        assert config.reviewers[1].model_id == "gemini-pro-3-1"
        assert config.consolidation is not None
        assert config.consolidation.model_id == "claude-opus-4-6"
        assert config.consensus.strategy == "majority"

    def test_raises_on_invalid_yaml(self, tmp_path):
        """Raises ReviewConfigError for invalid YAML."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        (config_dir / "review-config.yaml").write_text("{{invalid: yaml::")

        with pytest.raises(ReviewConfigError, match="Failed to parse YAML"):
            load_review_config(tmp_path)

    def test_raises_on_non_dict_yaml(self, tmp_path):
        """Raises ReviewConfigError when YAML is not a mapping."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        (config_dir / "review-config.yaml").write_text("- just\n- a\n- list\n")

        with pytest.raises(ReviewConfigError, match="must be a YAML mapping"):
            load_review_config(tmp_path)

    def test_raises_on_validation_failure(self, tmp_path):
        """Raises ReviewConfigError when config fails validation."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "unknown-model", "role": "primary"}],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="unknown model"):
            load_review_config(tmp_path)

    def test_loads_config_with_file_filters(self, tmp_path):
        """Loads config with file filters."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [
                    {"model_id": "claude-opus-4-6", "role": "primary"},
                ],
                "file_filters": {
                    "include": ["src/**", "lib/**"],
                    "exclude": ["**/*.test.ts"],
                },
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        config = load_review_config(tmp_path)
        assert config.file_filters.include == ["src/**", "lib/**"]
        assert config.file_filters.exclude == ["**/*.test.ts"]

    def test_loads_config_with_trigger_overrides(self, tmp_path):
        """Loads config with trigger overrides."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [
                    {"model_id": "claude-opus-4-6", "role": "primary"},
                ],
                "triggers": [
                    {
                        "type": "pr-label",
                        "label": "ai-review-quick",
                        "override": {
                            "max_reviewers": 1,
                            "skip_consolidation": True,
                        },
                    },
                ],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        config = load_review_config(tmp_path)
        assert len(config.triggers) == 1
        assert config.triggers[0].override is not None
        assert config.triggers[0].override.skip_consolidation is True
        assert config.triggers[0].override.max_reviewers == 1

    def test_raises_on_non_dict_review_section(self, tmp_path):
        """Raises ReviewConfigError when 'review' is not a mapping."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        (config_dir / "review-config.yaml").write_text("version: 1\nreview: not-a-dict\n")

        with pytest.raises(ReviewConfigError, match="must be a mapping"):
            load_review_config(tmp_path)

    def test_raises_on_non_list_reviewers(self, tmp_path):
        """Raises ReviewConfigError when reviewers is not a list."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {"version": 1, "review": {"reviewers": "not-a-list"}}
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="review.reviewers must be a list"):
            load_review_config(tmp_path)

    def test_raises_on_non_dict_reviewer_entry(self, tmp_path):
        """Raises ReviewConfigError when a reviewer entry is not a mapping."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {"version": 1, "review": {"reviewers": ["not-a-dict"]}}
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match=r"review\.reviewers\[0\] must be a mapping"):
            load_review_config(tmp_path)

    def test_raises_on_non_dict_consolidation(self, tmp_path):
        """Raises ReviewConfigError when consolidation is not a mapping."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "consolidation": "not-a-dict",
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="review.consolidation must be a mapping"):
            load_review_config(tmp_path)

    def test_raises_on_non_dict_consensus(self, tmp_path):
        """Raises ReviewConfigError when consensus is not a mapping."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "consensus": "not-a-dict",
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="review.consensus must be a mapping"):
            load_review_config(tmp_path)

    def test_raises_on_non_list_triggers(self, tmp_path):
        """Raises ReviewConfigError when triggers is not a list."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "triggers": "not-a-list",
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="review.triggers must be a list"):
            load_review_config(tmp_path)

    def test_raises_on_non_dict_trigger_entry(self, tmp_path):
        """Raises ReviewConfigError when a trigger entry is not a mapping."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "triggers": ["not-a-dict"],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match=r"review\.triggers\[0\] must be a mapping"):
            load_review_config(tmp_path)

    def test_raises_on_non_dict_file_filters(self, tmp_path):
        """Raises ReviewConfigError when file_filters is not a mapping."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "file_filters": "not-a-dict",
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="review.file_filters must be a mapping"):
            load_review_config(tmp_path)

    def test_raises_on_non_list_file_filters_include(self, tmp_path):
        """Raises ReviewConfigError when file_filters.include is not a list."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "file_filters": {"include": "not-a-list"},
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="file_filters.include must be a list"):
            load_review_config(tmp_path)

    def test_raises_on_non_string_file_filters_include_entry(self, tmp_path):
        """Raises ReviewConfigError when file_filters.include entry is not a string."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "file_filters": {"include": [42]},
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match=r"file_filters\.include\[0\] must be a string"):
            load_review_config(tmp_path)

    def test_raises_on_non_dict_trigger_override(self, tmp_path):
        """Raises ReviewConfigError when trigger override is not a mapping."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "triggers": [
                    {"type": "pr-label", "label": "test", "override": "not-a-dict"},
                ],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="trigger override.*must be a mapping"):
            load_review_config(tmp_path)

    def test_raises_on_non_int_max_reviewers_override(self, tmp_path):
        """Raises ReviewConfigError when override max_reviewers is not castable to int."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "triggers": [
                    {
                        "type": "pr-label",
                        "label": "test",
                        "override": {"max_reviewers": "not-an-int"},
                    },
                ],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="max_reviewers must be an integer"):
            load_review_config(tmp_path)

    def test_raises_on_non_bool_skip_consolidation_override(self, tmp_path):
        """Raises ReviewConfigError when override skip_consolidation is not a bool."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "triggers": [
                    {
                        "type": "pr-label",
                        "label": "test",
                        "override": {"skip_consolidation": "not-a-bool"},
                    },
                ],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="skip_consolidation must be a boolean"):
            load_review_config(tmp_path)

    def test_raises_on_non_string_consensus_strategy_override(self, tmp_path):
        """Raises ReviewConfigError when override consensus_strategy is not a string."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "triggers": [
                    {
                        "type": "pr-label",
                        "label": "test",
                        "override": {"consensus_strategy": 42},
                    },
                ],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="consensus_strategy must be a string"):
            load_review_config(tmp_path)

    def test_loads_config_from_yml_extension(self, tmp_path):
        """Loads config from .agdt/review-config.yml (alternate extension)."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [
                    {"model_id": "claude-opus-4-6", "role": "primary"},
                ],
                "triggers": [
                    {"type": "pr-label", "label": "ai-review"},
                ],
            },
        }
        (config_dir / "review-config.yml").write_text(yaml.dump(config_data))

        config = load_review_config(tmp_path)
        assert len(config.reviewers) == 1
        assert config.reviewers[0].model_id == "claude-opus-4-6"

    def test_yaml_extension_preferred_over_yml(self, tmp_path):
        """When both .yaml and .yml exist, .yaml is preferred."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        yaml_config = {
            "version": 1,
            "review": {
                "reviewers": [
                    {"model_id": "claude-opus-4-6", "role": "primary"},
                ],
                "triggers": [
                    {"type": "pr-label", "label": "ai-review"},
                ],
            },
        }
        yml_config = {
            "version": 1,
            "review": {
                "reviewers": [
                    {"model_id": "gemini-pro-3-1", "role": "primary"},
                ],
                "triggers": [
                    {"type": "pr-label", "label": "ai-review"},
                ],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(yaml_config))
        (config_dir / "review-config.yml").write_text(yaml.dump(yml_config))

        config = load_review_config(tmp_path)
        # .yaml takes priority
        assert config.reviewers[0].model_id == "claude-opus-4-6"

    def test_raises_on_non_list_file_filters_exclude(self, tmp_path):
        """Raises ReviewConfigError when file_filters.exclude is not a list."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "file_filters": {"exclude": "not-a-list"},
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="file_filters.exclude must be a list"):
            load_review_config(tmp_path)

    def test_raises_on_non_string_file_filters_exclude_entry(self, tmp_path):
        """Raises ReviewConfigError when file_filters.exclude entry is not a string."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "file_filters": {"exclude": [42]},
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match=r"file_filters\.exclude\[0\] must be a string"):
            load_review_config(tmp_path)

    def test_loads_valid_consensus_strategy_override(self, tmp_path):
        """Valid consensus_strategy override is parsed correctly."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "triggers": [
                    {
                        "type": "pr-label",
                        "label": "ai-review-full",
                        "override": {"consensus_strategy": "unanimous"},
                    },
                ],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        config = load_review_config(tmp_path)
        assert config.triggers[0].override is not None
        assert config.triggers[0].override.consensus_strategy == "unanimous"

    def test_raises_on_non_int_consensus_min_reviewers(self, tmp_path):
        """Raises ReviewConfigError when consensus.min_reviewers is not an int."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "consensus": {"min_reviewers": "not-a-number"},
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="consensus.min_reviewers must be an integer"):
            load_review_config(tmp_path)

    def test_raises_on_non_int_consensus_max_reviewers(self, tmp_path):
        """Raises ReviewConfigError when consensus.max_reviewers is not an int."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "consensus": {"max_reviewers": "not-a-number"},
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="consensus.max_reviewers must be an integer"):
            load_review_config(tmp_path)

    def test_raises_on_non_int_version(self, tmp_path):
        """Raises ReviewConfigError when version is not an int."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": "not-a-number",
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="version must be an integer"):
            load_review_config(tmp_path)

    def test_raises_on_bool_consensus_min_reviewers(self, tmp_path):
        """Rejects boolean True for consensus.min_reviewers (bool is int subclass)."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "consensus": {"min_reviewers": True},
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="consensus.min_reviewers must be an integer, got boolean"):
            load_review_config(tmp_path)

    def test_raises_on_float_consensus_max_reviewers(self, tmp_path):
        """Rejects float for consensus.max_reviewers."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "consensus": {"max_reviewers": 1.5},
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="consensus.max_reviewers must be an integer, got float"):
            load_review_config(tmp_path)

    def test_raises_on_bool_max_reviewers_override(self, tmp_path):
        """Rejects boolean True for trigger override max_reviewers."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "triggers": [
                    {
                        "type": "pr-label",
                        "label": "test",
                        "override": {"max_reviewers": True},
                    },
                ],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="max_reviewers must be an integer, got boolean"):
            load_review_config(tmp_path)

    def test_raises_on_bool_version(self, tmp_path):
        """Rejects boolean True for version (bool is int subclass)."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": True,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="version must be an integer, got boolean"):
            load_review_config(tmp_path)

    def test_raises_on_non_string_trigger_type(self, tmp_path):
        """Raises ReviewConfigError when trigger type is not a string."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "triggers": [{"type": 42, "label": "ai-review"}],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="trigger type must be a string"):
            load_review_config(tmp_path)

    def test_raises_on_non_string_trigger_label(self, tmp_path):
        """Raises ReviewConfigError when trigger label is not a string."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "triggers": [{"type": "pr-label", "label": 42}],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="trigger label must be a string"):
            load_review_config(tmp_path)

    def test_null_trigger_type_treated_as_empty(self, tmp_path):
        """YAML null trigger type is treated as empty string (fails validation)."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        # Write YAML manually because yaml.dump would omit null differently
        (config_dir / "review-config.yaml").write_text(
            "version: 1\n"
            "review:\n"
            "  reviewers:\n"
            "    - model_id: claude-opus-4-6\n"
            "      role: primary\n"
            "  triggers:\n"
            "    - type: null\n"
            "      label: ai-review\n"
        )

        # null type → empty string → validation error (must be 'pr-label')
        with pytest.raises(ReviewConfigError, match="must be 'pr-label'"):
            load_review_config(tmp_path)

    def test_null_trigger_label_treated_as_empty(self, tmp_path):
        """YAML null trigger label is treated as empty string (fails validation)."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        (config_dir / "review-config.yaml").write_text(
            "version: 1\n"
            "review:\n"
            "  reviewers:\n"
            "    - model_id: claude-opus-4-6\n"
            "      role: primary\n"
            "  triggers:\n"
            "    - type: pr-label\n"
            "      label: null\n"
        )

        # null label → empty string → validation error (must be non-empty)
        with pytest.raises(ReviewConfigError, match="must be non-empty"):
            load_review_config(tmp_path)

    def test_raises_on_non_string_reviewer_model_id(self, tmp_path):
        """Raises ReviewConfigError when reviewer model_id is not a string."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": 42, "role": "primary"}],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match=r"reviewer\.model_id must be a string"):
            load_review_config(tmp_path)

    def test_raises_on_null_reviewer_model_id(self, tmp_path):
        """Raises ReviewConfigError when reviewer model_id is YAML null."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        (config_dir / "review-config.yaml").write_text(
            "version: 1\nreview:\n  reviewers:\n    - model_id: null\n      role: primary\n"
        )

        with pytest.raises(ReviewConfigError, match=r"reviewer\.model_id must be a string.*null"):
            load_review_config(tmp_path)

    def test_raises_on_non_string_reviewer_role(self, tmp_path):
        """Raises ReviewConfigError when reviewer role is not a string."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": 123}],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match=r"reviewer\.role must be a string"):
            load_review_config(tmp_path)

    def test_raises_on_non_string_consolidation_model_id(self, tmp_path):
        """Raises ReviewConfigError when consolidation model_id is not a string."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "consolidation": {"model_id": 42, "role": "consolidator"},
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match=r"consolidation\.model_id must be a string"):
            load_review_config(tmp_path)

    def test_raises_on_null_consolidation_model_id(self, tmp_path):
        """Raises ReviewConfigError when consolidation model_id is YAML null."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        (config_dir / "review-config.yaml").write_text(
            "version: 1\n"
            "review:\n"
            "  reviewers:\n"
            "    - model_id: claude-opus-4-6\n"
            "      role: primary\n"
            "  consolidation:\n"
            "    model_id: null\n"
            "    role: consolidator\n"
        )

        with pytest.raises(ReviewConfigError, match=r"consolidation\.model_id must be a string.*null"):
            load_review_config(tmp_path)

    def test_raises_on_non_string_consensus_strategy(self, tmp_path):
        """Raises ReviewConfigError when consensus strategy is not a string."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "consensus": {"strategy": 42},
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match=r"consensus\.strategy must be a string"):
            load_review_config(tmp_path)

    def test_null_consensus_strategy_uses_default(self, tmp_path):
        """YAML null consensus strategy falls back to 'majority' default."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        (config_dir / "review-config.yaml").write_text(
            "version: 1\n"
            "review:\n"
            "  reviewers:\n"
            "    - model_id: claude-opus-4-6\n"
            "      role: primary\n"
            "  consensus:\n"
            "    strategy: null\n"
        )

        config = load_review_config(tmp_path)
        assert config.consensus.strategy == "majority"

    def test_reviewer_missing_model_id_defaults_to_empty(self, tmp_path):
        """Reviewer with no model_id key defaults to empty string (fails validation)."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"role": "primary"}],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="unknown model"):
            load_review_config(tmp_path)

    def test_reviewer_missing_role_defaults_to_empty(self, tmp_path):
        """Reviewer with no role key defaults to empty string (fails validation)."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6"}],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="role"):
            load_review_config(tmp_path)

    def test_consolidation_missing_model_id_defaults_to_empty(self, tmp_path):
        """Consolidation with no model_id key defaults to empty string (fails validation)."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "consolidation": {"role": "consolidator"},
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="unknown model"):
            load_review_config(tmp_path)

    def test_consolidation_missing_role_uses_default(self, tmp_path):
        """Consolidation with no role key defaults to 'consolidator'."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "consolidation": {"model_id": "claude-opus-4-6"},
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        config = load_review_config(tmp_path)
        assert config.consolidation.role == "consolidator"

    def test_raises_on_empty_list_consensus(self, tmp_path):
        """Raises ReviewConfigError when consensus is an empty list (falsy non-dict)."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "consensus": [],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="review.consensus must be a mapping"):
            load_review_config(tmp_path)

    def test_raises_on_empty_list_file_filters(self, tmp_path):
        """Raises ReviewConfigError when file_filters is an empty list (falsy non-dict)."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_data = {
            "version": 1,
            "review": {
                "reviewers": [{"model_id": "claude-opus-4-6", "role": "primary"}],
                "file_filters": [],
            },
        }
        (config_dir / "review-config.yaml").write_text(yaml.dump(config_data))

        with pytest.raises(ReviewConfigError, match="review.file_filters must be a mapping"):
            load_review_config(tmp_path)

    def test_raises_on_os_error(self, tmp_path):
        """Raises ReviewConfigError when config file cannot be read."""
        config_dir = tmp_path / ".agdt"
        config_dir.mkdir()
        config_file = config_dir / "review-config.yaml"
        config_file.write_text("version: 1")

        # Mock read_text to raise OSError — avoids relying on POSIX chmod
        # which is not reliable across platforms/filesystems.
        with patch.object(type(config_file), "read_text", side_effect=OSError("Permission denied")):
            with pytest.raises(ReviewConfigError, match="Failed to read config file"):
                load_review_config(tmp_path)
