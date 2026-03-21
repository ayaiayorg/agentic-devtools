"""
Project-level configuration stored in ``.agdt/config/project.json``.

This file is per-repo, versionable, and shareable across the team.
It stores project-specific settings such as Jira project keys,
corporate/VPN hostnames, and the Jira base URL.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

_CONFIG_DIR = "config"
_CONFIG_FILENAME = "project.json"


def _get_config_path() -> Optional[Path]:
    """Return the path to ``.agdt/config/project.json`` or ``None``."""
    # Deferred import to avoid circular dependency
    from agentic_devtools.state import _get_git_repo_root

    git_root = _get_git_repo_root()
    if git_root is None:
        return None
    return git_root / ".agdt" / _CONFIG_DIR / _CONFIG_FILENAME


def load_project_config() -> Dict[str, Any]:
    """Read ``.agdt/config/project.json`` and return its contents.

    Returns ``{}`` when the file does not exist, the current directory is
    not inside a git repository, or the JSON is malformed.
    """
    config_path = _get_config_path()
    if config_path is None or not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(
            f"Warning: Malformed JSON in {config_path}. Using empty config.",
            file=sys.stderr,
        )
        return {}


def save_project_config(config: Dict[str, Any]) -> Path:
    """Write *config* to ``.agdt/config/project.json``, creating directories as needed.

    Returns the path that was written.

    Raises ``RuntimeError`` if the git repository root cannot be determined.
    """
    config_path = _get_config_path()
    if config_path is None:
        raise RuntimeError("Cannot determine git repository root. Run from inside a git repo.")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return config_path


def get_project_config_value(key: str) -> Optional[str]:
    """Return a single value from the project config, or ``None``."""
    value = load_project_config().get(key)
    if value is None:
        return None
    return str(value)
