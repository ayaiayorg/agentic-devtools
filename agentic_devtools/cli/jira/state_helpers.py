"""
Jira state namespace helpers.
"""

from typing import Any, Optional

from agentic_devtools.state import get_value, set_value

# State namespace for Jira-related values
JIRA_STATE_NAMESPACE = "jira"


def get_jira_value(key: str, required: bool = False) -> Optional[Any]:
    """
    Get a value from the jira namespace in state.

    This is a convenience wrapper around get_value that prepends 'jira.' to keys.

    Args:
        key: Key within jira namespace (e.g., 'summary' -> 'jira.summary')
        required: If True, raise error when key doesn't exist

    Returns:
        Value or None if not found
    """
    return get_value(f"{JIRA_STATE_NAMESPACE}.{key}", required=required)


def set_jira_value(key: str, value: Any) -> None:
    """
    Set a value in the jira namespace in state.

    This is a convenience wrapper around set_value that prepends 'jira.' to keys.

    Args:
        key: Key within jira namespace (e.g., 'summary' -> 'jira.summary')
        value: Value to store
    """
    set_value(f"{JIRA_STATE_NAMESPACE}.{key}", value)
