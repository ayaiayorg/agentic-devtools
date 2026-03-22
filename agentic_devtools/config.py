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

logger = logging.getLogger(__name__)

CONFIG_FILE = ".github/agdt-config.json"

# Platform configuration constants
VALID_ISSUE_ADAPTERS: set[str] = {"jira", "github", "markdown"}
VALID_CODE_HOSTING: set[str] = {"github", "azure_devops", "other"}
DEFAULT_ISSUE_ADAPTER: str = "jira"
DEFAULT_CODE_HOSTING: str = "other"


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
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            logger.warning(
                "Expected a JSON object in %s, got %s; ignoring.",
                config_path,
                type(parsed).__name__,
            )
            return {}
        return parsed
    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON in %s: %s", config_path, exc)
        return {}
    except OSError as exc:
        logger.warning("Could not read %s: %s", config_path, exc)
        return {}


def load_review_focus_areas(repo_path: str) -> str | None:
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

    review_section = config.get("review")
    if review_section is None:
        return None
    if not isinstance(review_section, dict):
        logger.warning(
            "Expected 'review' section in %s to be an object, got %s; ignoring.",
            CONFIG_FILE,
            type(review_section).__name__,
        )
        return None

    focus_areas_file = review_section.get("focus-areas-file")
    if not focus_areas_file:
        return None
    if not isinstance(focus_areas_file, str):
        logger.warning(
            "Expected 'review.focus-areas-file' in %s to be a string, got %s; ignoring.",
            CONFIG_FILE,
            type(focus_areas_file).__name__,
        )
        return None

    repo_root = Path(repo_path).resolve()
    focus_path = (repo_root / focus_areas_file).resolve()

    # Reject paths that escape the repository root (path traversal guard).
    try:
        focus_path.relative_to(repo_root)
    except ValueError:
        logger.warning(
            "Configured focus-areas-file path %s escapes repository root %s; ignoring.",
            focus_path,
            repo_root,
        )
        return None

    if not focus_path.exists():
        logger.warning("focus-areas-file not found: %s", focus_path)
        return None

    try:
        return focus_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not read focus-areas-file %s: %s", focus_path, exc)
        return None


def load_platform_config(repo_path: str) -> dict:
    """
    Load the ``platform`` section from `.github/agdt-config.json`.

    Returns a dict with all platform keys guaranteed present, using safe
    defaults for any that are missing or invalid.  Unknown keys in the
    ``platform`` section are silently preserved for forward-compatibility.

    Args:
        repo_path: Absolute (or relative) path to the root of the target repo.

    Returns:
        Dict with at least ``issue_adapter``, ``code_hosting``, ``jira``,
        ``github``, and ``azure_devops`` keys.
    """
    config = load_repo_config(repo_path)
    platform = config.get("platform")

    if platform is None:
        platform = {}
    elif not isinstance(platform, dict):
        logger.warning(
            "Expected 'platform' section in %s to be an object, got %s; using defaults.",
            CONFIG_FILE,
            type(platform).__name__,
        )
        platform = {}

    # Validate issue_adapter enum.
    issue_adapter = platform.get("issue_adapter", DEFAULT_ISSUE_ADAPTER)
    if not isinstance(issue_adapter, str) or issue_adapter not in VALID_ISSUE_ADAPTERS:
        logger.warning(
            "Invalid issue_adapter value %r in %s; using default %r.",
            issue_adapter,
            CONFIG_FILE,
            DEFAULT_ISSUE_ADAPTER,
        )
        issue_adapter = DEFAULT_ISSUE_ADAPTER

    # Validate code_hosting enum.
    code_hosting = platform.get("code_hosting", DEFAULT_CODE_HOSTING)
    if not isinstance(code_hosting, str) or code_hosting not in VALID_CODE_HOSTING:
        logger.warning(
            "Invalid code_hosting value %r in %s; using default %r.",
            code_hosting,
            CONFIG_FILE,
            DEFAULT_CODE_HOSTING,
        )
        code_hosting = DEFAULT_CODE_HOSTING

    # Validate platform-specific sub-dicts (None from JSON null is also replaced).
    for key in ("jira", "github", "azure_devops"):
        value = platform.get(key)
        if not isinstance(value, dict):
            if value is not None:
                logger.warning(
                    "Expected 'platform.%s' in %s to be an object, got %s; using empty dict.",
                    key,
                    CONFIG_FILE,
                    type(value).__name__,
                )
            platform[key] = {}

    result = {**platform}
    result["issue_adapter"] = issue_adapter
    result["code_hosting"] = code_hosting
    result.setdefault("jira", {})
    result.setdefault("github", {})
    result.setdefault("azure_devops", {})

    return result


def save_platform_config(repo_path: str, platform_config: dict) -> bool:
    """
    Write the ``platform`` section to `.github/agdt-config.json`.

    Reads the existing config (if any), sets ``config["platform"]`` to
    *platform_config*, and writes the merged result back.  The ``.github/``
    directory and the config file are created when they do not exist.

    Args:
        repo_path: Absolute (or relative) path to the root of the target repo.
        platform_config: Dict to store as the ``platform`` section.

    Returns:
        ``True`` on success, ``False`` on failure (with a warning logged).
    """
    config = load_repo_config(repo_path)
    config["platform"] = platform_config

    config_path = Path(repo_path) / CONFIG_FILE
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        return True
    except OSError as exc:
        logger.warning("Could not write %s: %s", config_path, exc)
        return False
