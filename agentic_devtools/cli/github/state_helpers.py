"""
GitHub issue state namespace helpers.
"""

from typing import Any, Optional

from agentic_devtools.state import get_value, set_value

# State namespace for GitHub issue-related values
GITHUB_ISSUE_STATE_NAMESPACE = "issue"


def get_issue_value(key: str, required: bool = False) -> Optional[Any]:
    """
    Get a value from the issue namespace in state.

    This is a convenience wrapper around get_value that prepends 'issue.' to keys.

    Args:
        key: Key within issue namespace (e.g., 'title' -> 'issue.title')
        required: If True, raise error when key doesn't exist

    Returns:
        Value or None if not found
    """
    return get_value(f"{GITHUB_ISSUE_STATE_NAMESPACE}.{key}", required=required)


def set_issue_value(key: str, value: Any) -> None:
    """
    Set a value in the issue namespace in state.

    This is a convenience wrapper around set_value that prepends 'issue.' to keys.

    Args:
        key: Key within issue namespace (e.g., 'title' -> 'issue.title')
        value: Value to store
    """
    set_value(f"{GITHUB_ISSUE_STATE_NAMESPACE}.{key}", value)
