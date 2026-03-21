"""Configurable multi-model review pipeline configuration.

Defines the YAML schema for ``.agdt/review-config.yaml`` in target repos,
including typed dataclasses, validation, loading, trigger override resolution,
file filtering, and mechanical consensus logic.
"""

import logging
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CONFIG_PATHS = (".agdt/review-config.yaml", ".agdt/review-config.yml")

KNOWN_MODEL_IDS: frozenset = frozenset({"claude-opus-4-6", "gemini-pro-3-1", "gpt-codex-5-3"})

VALID_STRATEGIES = frozenset({"majority", "unanimous", "first-reviewer-wins"})

VALID_REVIEWER_ROLES = frozenset({"primary", "secondary", "tertiary"})

VALID_CONSOLIDATOR_ROLE = "consolidator"


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class ReviewConfigError(Exception):
    """Raised when the review configuration is invalid or malformed."""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ReviewerConfig:
    """A single reviewer model entry."""

    model_id: str
    role: str

    def validate(self, errors: list[str], index: int) -> None:
        """Append validation errors for this reviewer to *errors*."""
        if self.model_id not in KNOWN_MODEL_IDS:
            errors.append(f"reviewers[{index}].model_id: unknown model '{self.model_id}'")
        if self.role not in VALID_REVIEWER_ROLES:
            errors.append(f"reviewers[{index}].role: must be one of {sorted(VALID_REVIEWER_ROLES)}, got '{self.role}'")


@dataclass
class ConsolidationConfig:
    """Consolidator model configuration."""

    model_id: str
    role: str = VALID_CONSOLIDATOR_ROLE

    def validate(self, errors: list[str]) -> None:
        """Append validation errors for consolidation to *errors*."""
        if self.model_id not in KNOWN_MODEL_IDS:
            errors.append(f"consolidation.model_id: unknown model '{self.model_id}'")
        if self.role != VALID_CONSOLIDATOR_ROLE:
            errors.append(f"consolidation.role: must be '{VALID_CONSOLIDATOR_ROLE}', got '{self.role}'")


@dataclass
class ConsensusConfig:
    """Consensus strategy configuration."""

    strategy: str = "majority"
    min_reviewers: int = 2
    max_reviewers: int = 3

    def validate(self, errors: list[str]) -> None:
        """Append validation errors for consensus to *errors*."""
        if self.strategy not in VALID_STRATEGIES:
            errors.append(f"consensus.strategy: must be one of {sorted(VALID_STRATEGIES)}, got '{self.strategy}'")
        if self.min_reviewers < 1:
            errors.append("consensus.min_reviewers: must be >= 1")
        if self.max_reviewers < self.min_reviewers:
            errors.append("consensus.max_reviewers: must be >= min_reviewers")


@dataclass
class TriggerOverride:
    """Override settings applied when a specific label triggers the review."""

    max_reviewers: int | None = None
    skip_consolidation: bool | None = None
    consensus_strategy: str | None = None

    def validate(self, errors: list[str], label: str) -> None:
        """Append validation errors for this override to *errors*."""
        if self.consensus_strategy is not None and self.consensus_strategy not in VALID_STRATEGIES:
            errors.append(
                f"triggers[label={label}].override.consensus_strategy: "
                f"must be one of {sorted(VALID_STRATEGIES)}, "
                f"got '{self.consensus_strategy}'"
            )
        if self.max_reviewers is not None and self.max_reviewers < 1:
            errors.append(f"triggers[label={label}].override.max_reviewers: must be >= 1")


@dataclass
class TriggerConfig:
    """A single trigger entry."""

    type: str
    label: str
    override: TriggerOverride | None = None

    def validate(self, errors: list[str], index: int) -> None:
        """Append validation errors for this trigger to *errors*."""
        if self.type != "pr-label":
            errors.append(f"triggers[{index}].type: must be 'pr-label', got '{self.type}'")
        if not self.label:
            errors.append(f"triggers[{index}].label: must be non-empty")
        if self.override is not None:
            self.override.validate(errors, self.label)


@dataclass
class FileFilterConfig:
    """File include/exclude patterns."""

    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)


@dataclass
class ReviewConfig:
    """Top-level review pipeline configuration."""

    version: int = 1
    reviewers: list[ReviewerConfig] = field(default_factory=list)
    consolidation: ConsolidationConfig | None = None
    consensus: ConsensusConfig = field(default_factory=ConsensusConfig)
    triggers: list[TriggerConfig] = field(default_factory=list)
    file_filters: FileFilterConfig = field(default_factory=FileFilterConfig)

    # Runtime flag: True when consolidation should be skipped.
    skip_consolidation: bool = False

    def validate(self) -> None:
        """Validate entire config. Raises :class:`ReviewConfigError` on failure."""
        errors: list[str] = []

        if self.version != 1:
            errors.append(f"version: must be 1, got {self.version}")

        if not self.reviewers:
            errors.append("reviewers: must contain at least one reviewer")

        for i, rev in enumerate(self.reviewers):
            rev.validate(errors, i)

        if self.consolidation is not None:
            self.consolidation.validate(errors)

        self.consensus.validate(errors)

        for i, trigger in enumerate(self.triggers):
            trigger.validate(errors, i)

        if errors:
            raise ReviewConfigError("Review config validation failed:\n- " + "\n- ".join(errors))


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_int_field(section: str, field_name: str, raw_value: Any) -> int:
    """Parse a config field that must be an integer, with strict type checks.

    Rejects booleans and non-integer numeric types (e.g. floats) to avoid
    surprising coercions from YAML such as ``true`` → ``1`` or ``1.9`` → ``1``.
    """
    qualified = f"{section}.{field_name}" if section else field_name

    # Bool is a subclass of int, but we never want to accept it here.
    if isinstance(raw_value, bool):
        raise ReviewConfigError(f"{qualified} must be an integer, got boolean value {raw_value!r}")

    if isinstance(raw_value, int):
        return raw_value

    if isinstance(raw_value, str):
        stripped = raw_value.strip()
        if stripped.isdigit() or (len(stripped) > 1 and stripped.startswith("-") and stripped[1:].isdigit()):
            return int(stripped)
        raise ReviewConfigError(f"{qualified} must be an integer, got string value {raw_value!r}")

    raise ReviewConfigError(f"{qualified} must be an integer, got {type(raw_value).__name__} value {raw_value!r}")


def _require_str(section: str, field_name: str, value: Any) -> str:
    """Ensure a config value is a string, raising ReviewConfigError otherwise.

    This is used instead of ``str(...)`` coercion so that YAML ``null`` values
    and non-string types produce clear, targeted error messages.
    """
    if value is None:
        raise ReviewConfigError(f"{section}.{field_name} must be a string, got null")
    if not isinstance(value, str):
        raise ReviewConfigError(f"{section}.{field_name} must be a string, got {value!r} ({type(value).__name__})")
    return value


def _parse_reviewer(data: dict[str, Any]) -> ReviewerConfig:
    if "model_id" in data:
        model_id = _require_str("reviewer", "model_id", data["model_id"])
    else:
        model_id = ""

    if "role" in data:
        role = _require_str("reviewer", "role", data["role"])
    else:
        role = ""

    return ReviewerConfig(
        model_id=model_id,
        role=role,
    )


def _parse_consolidation(data: dict[str, Any]) -> ConsolidationConfig:
    if "model_id" in data:
        model_id = _require_str("consolidation", "model_id", data["model_id"])
    else:
        model_id = ""

    if "role" in data:
        role = _require_str("consolidation", "role", data["role"])
    else:
        role = VALID_CONSOLIDATOR_ROLE

    return ConsolidationConfig(
        model_id=model_id,
        role=role,
    )


def _parse_consensus(data: dict[str, Any]) -> ConsensusConfig:
    """Parse and type-validate the consensus section from raw YAML data."""
    min_reviewers = _parse_int_field("consensus", "min_reviewers", data.get("min_reviewers", 2))
    max_reviewers = _parse_int_field("consensus", "max_reviewers", data.get("max_reviewers", 3))

    raw_strategy = data.get("strategy")
    if raw_strategy is None:
        strategy = "majority"
    elif isinstance(raw_strategy, str):
        strategy = raw_strategy
    else:
        raise ReviewConfigError(f"consensus.strategy must be a string, got {type(raw_strategy).__name__}")

    return ConsensusConfig(
        strategy=strategy,
        min_reviewers=min_reviewers,
        max_reviewers=max_reviewers,
    )


def _parse_trigger_override(data: dict[str, Any]) -> TriggerOverride:
    """Parse and type-validate a trigger override section from raw YAML data."""
    raw_max = data.get("max_reviewers")
    if raw_max is not None:
        max_reviewers: int | None = _parse_int_field("trigger override", "max_reviewers", raw_max)
    else:
        max_reviewers = None

    raw_skip = data.get("skip_consolidation")
    if raw_skip is not None:
        if not isinstance(raw_skip, bool):
            raise ReviewConfigError(
                f"trigger override skip_consolidation must be a boolean, got {type(raw_skip).__name__}"
            )
        skip_consolidation: bool | None = raw_skip
    else:
        skip_consolidation = None

    raw_strategy = data.get("consensus_strategy")
    if raw_strategy is not None:
        if not isinstance(raw_strategy, str):
            raise ReviewConfigError(
                f"trigger override consensus_strategy must be a string, got {type(raw_strategy).__name__}"
            )
        consensus_strategy: str | None = raw_strategy
    else:
        consensus_strategy = None

    return TriggerOverride(
        max_reviewers=max_reviewers,
        skip_consolidation=skip_consolidation,
        consensus_strategy=consensus_strategy,
    )


def _parse_trigger(data: dict[str, Any]) -> TriggerConfig:
    override_data = data.get("override")
    override = None
    if override_data is not None:
        if not isinstance(override_data, dict):
            raise ReviewConfigError(f"trigger override for label '{data.get('label', '?')}' must be a mapping")
        override = _parse_trigger_override(override_data)

    raw_type = data.get("type", "")
    if raw_type is None:
        type_value = ""
    elif isinstance(raw_type, str):
        type_value = raw_type
    else:
        raise ReviewConfigError(f"trigger type must be a string, got {type(raw_type).__name__}")

    raw_label = data.get("label", "")
    if raw_label is None:
        label_value = ""
    elif isinstance(raw_label, str):
        label_value = raw_label
    else:
        raise ReviewConfigError(f"trigger label must be a string, got {type(raw_label).__name__}")

    return TriggerConfig(
        type=type_value,
        label=label_value,
        override=override,
    )


def _parse_file_filters(data: dict[str, Any]) -> FileFilterConfig:
    raw_include = data.get("include", [])
    raw_exclude = data.get("exclude", [])

    if not isinstance(raw_include, list):
        raise ReviewConfigError("file_filters.include must be a list of strings")
    if not isinstance(raw_exclude, list):
        raise ReviewConfigError("file_filters.exclude must be a list of strings")

    for idx, pattern in enumerate(raw_include):
        if not isinstance(pattern, str):
            raise ReviewConfigError(f"file_filters.include[{idx}] must be a string")
    for idx, pattern in enumerate(raw_exclude):
        if not isinstance(pattern, str):
            raise ReviewConfigError(f"file_filters.exclude[{idx}] must be a string")

    return FileFilterConfig(
        include=raw_include,
        exclude=raw_exclude,
    )


def _parse_review_config(data: dict[str, Any]) -> ReviewConfig:
    """Parse a raw YAML dict into a :class:`ReviewConfig`."""
    review = data.get("review", {})
    if not isinstance(review, dict):
        raise ReviewConfigError("'review' must be a mapping")

    # --- reviewers ---
    raw_reviewers = review.get("reviewers", [])
    if not isinstance(raw_reviewers, list):
        raise ReviewConfigError("review.reviewers must be a list")
    reviewers: list[ReviewerConfig] = []
    for idx, r in enumerate(raw_reviewers):
        if not isinstance(r, dict):
            raise ReviewConfigError(f"review.reviewers[{idx}] must be a mapping")
        reviewers.append(_parse_reviewer(r))

    # --- consolidation ---
    consolidation_data = review.get("consolidation")
    consolidation = None
    if consolidation_data is not None:
        if not isinstance(consolidation_data, dict):
            raise ReviewConfigError("review.consolidation must be a mapping")
        consolidation = _parse_consolidation(consolidation_data)

    # --- consensus ---
    consensus_data = review.get("consensus")
    if consensus_data is not None and not isinstance(consensus_data, dict):
        raise ReviewConfigError("review.consensus must be a mapping")
    if isinstance(consensus_data, dict):
        consensus = _parse_consensus(consensus_data)
    else:
        consensus = ConsensusConfig()

    # --- triggers ---
    raw_triggers = review.get("triggers", [])
    if not isinstance(raw_triggers, list):
        raise ReviewConfigError("review.triggers must be a list")
    triggers: list[TriggerConfig] = []
    for idx, t in enumerate(raw_triggers):
        if not isinstance(t, dict):
            raise ReviewConfigError(f"review.triggers[{idx}] must be a mapping")
        triggers.append(_parse_trigger(t))

    # --- file_filters ---
    filters_data = review.get("file_filters")
    if filters_data is not None and not isinstance(filters_data, dict):
        raise ReviewConfigError("review.file_filters must be a mapping")
    if isinstance(filters_data, dict):
        file_filters = _parse_file_filters(filters_data)
    else:
        file_filters = FileFilterConfig()

    version = _parse_int_field("", "version", data.get("version", 1))

    return ReviewConfig(
        version=version,
        reviewers=reviewers,
        consolidation=consolidation,
        consensus=consensus,
        triggers=triggers,
        file_filters=file_filters,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def default_review_config() -> ReviewConfig:
    """Return the built-in default config (single model, no consolidation)."""
    return ReviewConfig(
        version=1,
        reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
        consolidation=None,
        consensus=ConsensusConfig(strategy="majority", min_reviewers=1, max_reviewers=1),
        triggers=[
            TriggerConfig(type="pr-label", label="ai-review"),
        ],
        file_filters=FileFilterConfig(),
        skip_consolidation=True,
    )


def load_review_config(repo_root: Path) -> ReviewConfig:
    """Load review config from the target repo.

    Args:
        repo_root: Path to the repository root (local checkout).

    Returns:
        Parsed and validated :class:`ReviewConfig`.

    Raises:
        ReviewConfigError: If the file exists but is invalid.
    """
    config_path = None
    for candidate_path in _CONFIG_PATHS:
        candidate = repo_root / candidate_path
        if candidate.is_file():
            config_path = candidate
            break

    if config_path is None:
        logger.info("No .agdt/review-config.yaml or .yml found, using built-in defaults.")
        return default_review_config()

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ReviewConfigError(f"Failed to parse YAML: {exc}") from exc
    except OSError as exc:
        raise ReviewConfigError(f"Failed to read config file {config_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ReviewConfigError("Config file must be a YAML mapping at the top level")

    config = _parse_review_config(raw)
    config.validate()
    return config


def resolve_trigger_overrides(config: ReviewConfig, label: str) -> ReviewConfig:
    """Apply label-specific overrides and return a new config instance.

    If the label matches a trigger with an override block, the override
    values are merged into a copy of the config.

    Args:
        config: The base config.
        label: The PR label that triggered the review.

    Returns:
        A new :class:`ReviewConfig` with overrides applied.
    """
    import copy

    result = copy.deepcopy(config)

    for trigger in result.triggers:
        if trigger.label == label and trigger.override is not None:
            ovr = trigger.override
            if ovr.max_reviewers is not None:
                result.consensus.max_reviewers = ovr.max_reviewers
                result.reviewers = result.reviewers[: ovr.max_reviewers]
            if ovr.skip_consolidation is not None:
                result.skip_consolidation = ovr.skip_consolidation
            if ovr.consensus_strategy is not None:
                result.consensus.strategy = ovr.consensus_strategy
            break

    # Always enforce the max_reviewers cap — even when no trigger override
    # matched, the base config might have more reviewers than max_reviewers.
    if len(result.reviewers) > result.consensus.max_reviewers:
        result.reviewers = result.reviewers[: result.consensus.max_reviewers]

    # Ensure consensus invariants hold after applying overrides.  In particular,
    # a max_reviewers override may reduce the cap below the configured
    # min_reviewers; clamp min_reviewers down to max_reviewers so that
    # validate() does not fail for otherwise valid "quick review" overrides.
    if result.consensus.min_reviewers > result.consensus.max_reviewers:
        logger.debug(
            "Clamping consensus.min_reviewers from %s down to max_reviewers=%s after applying trigger overrides.",
            result.consensus.min_reviewers,
            result.consensus.max_reviewers,
        )
        result.consensus.min_reviewers = result.consensus.max_reviewers

    result.validate()

    return result


# ---------------------------------------------------------------------------
# File filtering
# ---------------------------------------------------------------------------


def _matches_pattern(filepath: str, pattern: str) -> bool:
    """Check if *filepath* matches a glob *pattern* using fnmatch.

    Supports ``**`` for recursive matching by checking the full path
    and all path suffixes (e.g. for ``src/app/file.ts`` the suffixes
    ``app/file.ts`` and ``file.ts`` are also tested).
    """
    # Normalise to forward slashes
    filepath = filepath.replace("\\", "/")
    pattern = pattern.replace("\\", "/")

    if fnmatch(filepath, pattern):
        return True
    # fnmatch treats * as matching everything including '/', so ** has no
    # special "recursive directory" meaning.  The suffix loop allows
    # patterns like "app/*.ts" to match "src/app/file.ts" by testing
    # every trailing path segment combination.
    parts = filepath.split("/")
    for i in range(len(parts)):
        if fnmatch("/".join(parts[i:]), pattern):
            return True
    return False


def filter_files(file_paths: list[str], filters: FileFilterConfig) -> list[str]:
    """Apply include/exclude filters to a list of file paths.

    Args:
        file_paths: List of file paths (forward-slash separated).
        filters: The file filter configuration.

    Returns:
        Filtered list of file paths.
    """
    result = file_paths

    if filters.include:
        result = [fp for fp in result if any(_matches_pattern(fp, pat) for pat in filters.include)]

    if filters.exclude:
        result = [fp for fp in result if not any(_matches_pattern(fp, pat) for pat in filters.exclude)]

    return result


# ---------------------------------------------------------------------------
# Mechanical consensus
# ---------------------------------------------------------------------------


def compute_mechanical_consensus(
    verdicts: list[str],
    strategy: str,
) -> str:
    """Determine file status mechanically from reviewer verdicts.

    Args:
        verdicts: List of status strings (e.g. ``['approved', 'needs-work']``).
        strategy: One of ``'majority'``, ``'unanimous'``, ``'first-reviewer-wins'``.

    Returns:
        ``'approved'`` or ``'needs-work'``.
    """
    if not verdicts:
        return "needs-work"

    if strategy == "first-reviewer-wins":
        # Normalize: any non-'approved' verdict is treated as 'needs-work'.
        return "approved" if verdicts[0] == "approved" else "needs-work"

    if strategy == "unanimous":
        # Only a unanimous 'approved' set yields 'approved'.
        if all(v == "approved" for v in verdicts):
            return "approved"
        return "needs-work"

    # majority (default)
    approved_count = sum(1 for v in verdicts if v == "approved")
    if approved_count > len(verdicts) / 2:
        return "approved"
    return "needs-work"
