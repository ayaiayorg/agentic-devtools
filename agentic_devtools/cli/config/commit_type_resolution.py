"""
Resolution and validation of commit issue types from project configuration.

Reads ``defaultCommitIssueType`` and ``availableCommitIssueTypes`` from
``.agdt/config/project.json``, resolving the effective commit type with a
deterministic priority chain and optional validation against allowed types.
"""

from __future__ import annotations

import sys
from typing import Any

STANDARD_COMMIT_TYPES: list[str] = [
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
]
"""The 11 standard Conventional Commits type prefixes."""

_MAX_DISPLAYED_TYPES = 20
"""Maximum number of allowed types shown in validation warning messages."""


def _escape_single_quote(value: str) -> str:
    """Escape a string for display inside single quotes in warning messages.

    Escapes backslashes first, then single quotes, so that the result can
    be safely wrapped in ``'...'`` without breaking the quoting.
    """
    return value.replace("\\", "\\\\").replace("'", "\\'")


def read_default_commit_type(
    project_config: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Read the default commit issue type from project configuration.

    Checks ``defaultCommitIssueType`` (camelCase canonical) first, then
    falls back to the ``default_commit_issue_type`` snake_case alias.

    Returns:
        A tuple of ``(value, warning)``.  *value* is the resolved string or
        ``None`` when absent/empty.  *warning* is a diagnostic message string
        when the config value has a non-string type, or ``None`` otherwise.
    """
    warning: str | None = None

    # camelCase takes precedence, but fall back to the snake_case alias when the
    # canonical value is missing/blank/invalid.
    for key in ("defaultCommitIssueType", "default_commit_issue_type"):
        if key not in project_config:
            continue

        raw = project_config[key]
        if not isinstance(raw, str):
            if warning is None:
                warning = f"Warning: '{key}' in project.json should be a string, got {type(raw).__name__}. Ignoring."
            continue

        stripped = raw.strip()
        if stripped:
            return stripped, warning

    return None, warning


def read_available_commit_types(
    project_config: dict[str, Any],
) -> tuple[list[str], str | None]:
    """Read the allowed commit issue types from project configuration.

    Checks ``availableCommitIssueTypes`` (camelCase canonical) first, then
    falls back to the ``available_commit_issue_types`` snake_case alias.

    Returns:
        A tuple of ``(types_list, warning)``.  *types_list* is the resolved
        list (falls back to :data:`STANDARD_COMMIT_TYPES` when absent or
        invalid).  *warning* is a diagnostic message string when the config
        value is malformed, or ``None`` otherwise.
    """
    warning: str | None = None

    for key in ("availableCommitIssueTypes", "available_commit_issue_types"):
        if key not in project_config:
            continue

        raw = project_config[key]
        if not isinstance(raw, list):
            if warning is None:
                warning = (
                    f"Warning: '{key}' in project.json should be an array, "
                    f"got {type(raw).__name__}. Using standard types."
                )
            continue

        if not raw:
            # Empty array → use standard types
            return list(STANDARD_COMMIT_TYPES), warning

        non_strings = [i for i, item in enumerate(raw) if not isinstance(item, str)]
        if non_strings:
            if warning is None:
                warning = (
                    f"Warning: '{key}' in project.json contains non-string "
                    f"elements at indices {non_strings}. Using standard types."
                )
            continue

        normalized = [item.strip() for item in raw]
        blank_indices = [i for i, item in enumerate(normalized) if not item]
        if blank_indices:
            if warning is None:
                warning = (
                    f"Warning: '{key}' in project.json contains blank entries "
                    f"at indices {blank_indices}. Using standard types."
                )
            continue

        return normalized, warning

    return list(STANDARD_COMMIT_TYPES), warning


def validate_commit_issue_type(
    issue_type: str,
    allowed_types: list[str],
) -> str | None:
    """Validate a commit issue type against an allowed list.

    Returns ``None`` when *issue_type* is found in *allowed_types*
    (case-sensitive comparison).  Otherwise returns a warning string
    identifying the invalid type and listing the allowed types.

    When *allowed_types* exceeds :data:`_MAX_DISPLAYED_TYPES` entries,
    only the first 19 are shown followed by ``'and N more'``.
    """
    if issue_type in allowed_types:
        return None

    escaped_type = _escape_single_quote(issue_type)

    if len(allowed_types) > _MAX_DISPLAYED_TYPES:
        displayed = [f"'{_escape_single_quote(t)}'" for t in allowed_types[:19]]
        remaining = len(allowed_types) - 19
        displayed.append(f"'and {remaining} more'")
    else:
        displayed = [f"'{_escape_single_quote(t)}'" for t in allowed_types]

    types_str = "[" + ", ".join(displayed) + "]"
    return f"Warning: Issue type '{escaped_type}' is not in availableCommitIssueTypes. Allowed: {types_str}"


def resolve_commit_issue_type(
    explicit_type: str | None = None,
    *,
    project_config: dict[str, Any] | None = None,
) -> tuple[str, list[str]]:
    """Resolve the effective commit issue type with full validation.

    Priority chain:
    1. *explicit_type* (from CLI arg or ``versionControl.commitMessageType`` state)
    2. ``defaultCommitIssueType`` from project config
    3. Hardcoded fallback: ``"feat"``

    When *project_config* is ``None``, calls :func:`load_project_config`
    internally.

    Returns:
        A tuple of ``(resolved_type, warnings)`` where *warnings* is a list
        of warning message strings (may be empty).
    """
    warnings: list[str] = []

    if project_config is None:
        from agentic_devtools.cli.config.project_config import load_project_config

        project_config = load_project_config()

    # Read available types first (needed for validation)
    available_types, available_warning = read_available_commit_types(project_config)
    if available_warning:
        warnings.append(available_warning)
        print(available_warning, file=sys.stderr)

    # Read config default
    config_default, default_warning = read_default_commit_type(project_config)
    if default_warning:
        warnings.append(default_warning)
        print(default_warning, file=sys.stderr)

    # Resolution chain
    resolved: str
    if explicit_type is not None and explicit_type.strip():
        resolved = explicit_type.strip()
    elif config_default is not None:
        resolved = config_default
    else:
        resolved = "feat"

    # Validate resolved type against allowed types
    validation_warning = validate_commit_issue_type(resolved, available_types)
    if validation_warning:
        # Check if this is a misconfigured default (FR-005): the warning should
        # indicate that the project config default itself is invalid, but only
        # if the resolved type came from project config (not explicit override).
        if explicit_type is None or not explicit_type.strip():
            if config_default is not None and resolved == config_default:
                # Rewrite as a misconfiguration warning
                validation_warning = (
                    f"Warning: defaultCommitIssueType '{_escape_single_quote(config_default)}' "
                    f"in project.json is not in availableCommitIssueTypes. "
                    f"Using it anyway, but consider updating your configuration."
                )
        warnings.append(validation_warning)
        print(validation_warning, file=sys.stderr)

    return resolved, warnings
