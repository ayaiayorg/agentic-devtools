"""
Repo-specific configuration loader for agentic-devtools.

Reads and validates `.github/agdt-config.json` from a target repository root,
exposing structured access to review focus areas and other repo-specific metadata.

Both the config file and any referenced files are optional — if missing, functions
return safe defaults so the review workflow proceeds without repo-specific context.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CONFIG_FILE = ".github/agdt-config.json"


def load_repo_config(repo_path: str) -> dict:
    """
    Load and return the parsed contents of `.github/agdt-config.json`.

    The config file is optional.  If it is absent, an empty dict is returned
    and no error is raised.  If the file exists but contains invalid JSON a
    warning is logged and an empty dict is returned.

    Args:
        repo_path: Absolute (or relative) path to the root of the target repo.

    Returns:
        Parsed config dict, or ``{}`` when the file is missing or unreadable.
    """
    config_path = Path(repo_path) / CONFIG_FILE
    if not config_path.exists():
        return {}

    try:
        content = config_path.read_text(encoding="utf-8")
        return json.loads(content)
    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON in %s: %s", config_path, exc)
        return {}


def load_review_focus_areas(repo_path: str) -> Optional[str]:
    """
    Load the review focus areas markdown content referenced in the repo config.

    Reads ``review.focus-areas-file`` from `.github/agdt-config.json`, then
    returns the raw markdown text of that file.  All files are optional — if
    either the config or the referenced markdown file is missing the function
    returns ``None`` without raising.

    Args:
        repo_path: Absolute (or relative) path to the root of the target repo.

    Returns:
        Raw markdown string, or ``None`` when no focus areas are configured.
    """
    config = load_repo_config(repo_path)
    focus_areas_file: Optional[str] = config.get("review", {}).get("focus-areas-file")
    if not focus_areas_file:
        return None

    focus_path = Path(repo_path) / focus_areas_file
    if not focus_path.exists():
        logger.warning("focus-areas-file not found: %s", focus_path)
        return None

    return focus_path.read_text(encoding="utf-8")
