"""``agdt-review config-get`` and ``agdt-review config-validate`` commands."""

import sys
from pathlib import Path
from typing import Any, Optional

import yaml

from agentic_devtools.cli.azure_devops.review_config import (
    ReviewConfigError,
    load_review_config,
)


def _resolve_repo_root(config_path: Optional[str]) -> Path:
    """Derive the repo root from an optional config path or repo root override.

    The argument may be either:
    - a path to the review config file (e.g. ".agdt/review-config.yaml"), or
    - a path to the repository root directory.
    """
    if not config_path:
        return Path.cwd()

    candidate = Path(config_path).expanduser().resolve()

    # If the path looks like a YAML file, assume it is the config file path.
    if candidate.suffix in {".yml", ".yaml"}:
        # Validate the canonical .agdt/review-config.* structure.
        if candidate.name not in {"review-config.yml", "review-config.yaml"} or candidate.parent.name != ".agdt":
            raise ReviewConfigError(
                f"Config path {candidate} must point to"
                " '.agdt/review-config.yaml' or '.agdt/review-config.yml'"
                " relative to the repository root."
            )
        # Ensure the referenced config file actually exists so that validation
        # does not silently fall back to the default configuration.
        if not candidate.is_file():
            raise ReviewConfigError(f"Config file {candidate} does not exist.")
        return candidate.parent.parent

    # Otherwise, treat the argument as the repo root directory.
    if not candidate.exists():
        raise ReviewConfigError(f"Repository root {candidate} does not exist.")
    if not candidate.is_dir():
        raise ReviewConfigError(f"Repository root {candidate} is not a directory.")
    return candidate


def _config_to_dict(config: object) -> Any:
    """Recursively convert dataclass instances to dicts for YAML output."""
    import dataclasses

    if dataclasses.is_dataclass(config) and not isinstance(config, type):
        result = {}
        for f in dataclasses.fields(config):
            value = getattr(config, f.name)
            result[f.name] = _config_to_dict(value)
        return result
    if isinstance(config, list):
        return [_config_to_dict(item) for item in config]
    if isinstance(config, dict):
        return {k: _config_to_dict(v) for k, v in config.items()}
    return config


def run_config_get(config_path: Optional[str] = None) -> None:
    """Read and display the target repo's review config (resolved)."""
    try:
        repo_root = _resolve_repo_root(config_path)
    except ReviewConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        config = load_review_config(repo_root)
    except ReviewConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    output = _config_to_dict(config)
    print(yaml.safe_dump(output, default_flow_style=False, sort_keys=False))


def run_config_validate(config_path: Optional[str] = None) -> None:
    """Validate config file syntax, schema, and model references."""
    try:
        repo_root = _resolve_repo_root(config_path)
    except ReviewConfigError as exc:
        print(f"Validation failed:\n{exc}", file=sys.stderr)
        sys.exit(1)

    try:
        load_review_config(repo_root)
    except ReviewConfigError as exc:
        print(f"Validation failed:\n{exc}", file=sys.stderr)
        sys.exit(1)

    print("Configuration valid.")
