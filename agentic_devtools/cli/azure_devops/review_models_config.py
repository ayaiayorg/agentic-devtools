"""Review models configuration for multi-model PR reviews.

Manages the configuration of AI reviewer models and the boss/consolidator model.
Configuration is loaded from ``.agdt/config/review-models.json`` with optional
override support via ``.agdt/config/review-models-override.json``.

Override files take full precedence — no merging is performed.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Relative paths under the repository root
_CONFIG_DIR = ".agdt/config"
_BASE_FILENAME = "review-models.json"
_OVERRIDE_FILENAME = "review-models-override.json"

# Default configuration written by agdt-setup when the file does not exist
_DEFAULT_REVIEWER_MODELS = ["Claude Opus 4.6"]
_DEFAULT_BOSS_MODEL = "Claude Opus 4.6"


@dataclass
class ReviewModelsConfig:
    """Configuration for multi-model PR reviews.

    Attributes:
        reviewerModels: Ordered list of AI model identifiers that will
            independently review each file.  The first model is the
            primary reviewer whose content populates the main comment.
        bossModel: Model used as the consolidator/tiebreaker when
            reviewers disagree.
    """

    reviewerModels: List[str] = field(default_factory=lambda: list(_DEFAULT_REVIEWER_MODELS))
    bossModel: str = _DEFAULT_BOSS_MODEL

    def to_dict(self) -> Dict:
        """Serialize to JSON-compatible dictionary."""
        return {
            "reviewerModels": list(self.reviewerModels),
            "bossModel": self.bossModel,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ReviewModelsConfig":
        """Deserialize from a dictionary.

        Raises:
            ValueError: If validation fails (empty model list, non-string entries, etc.).
        """
        reviewer_models = data.get("reviewerModels", list(_DEFAULT_REVIEWER_MODELS))
        boss_model = data.get("bossModel", _DEFAULT_BOSS_MODEL)
        config = cls(reviewerModels=reviewer_models, bossModel=boss_model)
        config.validate()
        return config

    def validate(self) -> None:
        """Validate the configuration.

        Raises:
            ValueError: If ``reviewerModels`` is empty, contains non-string or
                blank entries, or ``bossModel`` is blank.
        """
        if not isinstance(self.reviewerModels, list) or len(self.reviewerModels) == 0:
            raise ValueError("reviewerModels must be a non-empty list of model names.")
        for i, model in enumerate(self.reviewerModels):
            if not isinstance(model, str) or not model.strip():
                raise ValueError(f"reviewerModels[{i}] must be a non-empty string, got: {model!r}")
        if not isinstance(self.bossModel, str) or not self.bossModel.strip():
            raise ValueError(f"bossModel must be a non-empty string, got: {self.bossModel!r}")

    @property
    def is_multi_model(self) -> bool:
        """Return True if more than one reviewer model is configured."""
        return len(self.reviewerModels) > 1


def _config_dir(repo_path: str) -> Path:
    """Return the resolved path to the ``.agdt/config/`` directory."""
    return Path(repo_path).resolve() / _CONFIG_DIR


def load_review_models_config(repo_path: str) -> ReviewModelsConfig:
    """Load the review models configuration for a repository.

    Reads from ``{repo_path}/.agdt/config/review-models-override.json`` if it
    exists, otherwise falls back to ``review-models.json``.  If neither file
    exists, returns the default single-model configuration.

    Args:
        repo_path: Absolute (or relative) path to the root of the target repo.

    Returns:
        Validated ``ReviewModelsConfig``.

    Raises:
        ValueError: If the loaded JSON fails validation.
    """
    config_root = _config_dir(repo_path)
    override_path = config_root / _OVERRIDE_FILENAME
    base_path = config_root / _BASE_FILENAME

    chosen_path: Optional[Path] = None
    if override_path.exists():
        chosen_path = override_path
    elif base_path.exists():
        chosen_path = base_path

    if chosen_path is None:
        logger.info("No review-models config found at %s; using defaults.", config_root)
        return ReviewModelsConfig()

    try:
        content = chosen_path.read_text(encoding="utf-8")
        data = json.loads(content)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load %s: %s; using defaults.", chosen_path, exc)
        return ReviewModelsConfig()

    if not isinstance(data, dict):
        logger.warning("Expected JSON object in %s, got %s; using defaults.", chosen_path, type(data).__name__)
        return ReviewModelsConfig()

    return ReviewModelsConfig.from_dict(data)


def ensure_default_config(repo_path: str) -> Path:
    """Ensure the default review-models.json exists under ``.agdt/config/``.

    Creates the file with default content if it does not already exist.
    Never overwrites ``*-override.*`` files.

    Called by ``agdt-setup`` to install managed defaults.

    Args:
        repo_path: Absolute (or relative) path to the root of the target repo.

    Returns:
        Path to the written (or existing) base config file.
    """
    config_root = _config_dir(repo_path)
    base_path = config_root / _BASE_FILENAME

    config_root.mkdir(parents=True, exist_ok=True)

    default = ReviewModelsConfig()
    content = json.dumps(default.to_dict(), indent=2, ensure_ascii=False) + "\n"
    base_path.write_text(content, encoding="utf-8")

    return base_path
