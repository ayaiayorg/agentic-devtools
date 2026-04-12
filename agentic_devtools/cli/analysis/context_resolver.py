"""Resolve analysis context from parameters for workflow analysis.

This module provides helper functions for the ``agdt.analyze-workflow`` agent
to resolve the target worktree context from ``--issue-key`` or ``--pr-id``
parameters, and to discover state directories across identity directories.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentic_devtools.state import (
    _get_git_repo_root,
    get_bootstrap_state,
    get_state_dir,
    is_safe_dir_segment,
)


@dataclass(frozen=True)
class AnalysisContext:
    """Immutable context for a workflow analysis session.

    Attributes:
        worktree_key: The resolved worktree key (e.g. ``"PROJECT-123"`` or ``"PR42"``).
        source: How the worktree_key was determined (``"issue_key"``, ``"pr_id"``,
            or ``"bootstrap"``).
        git_root: Path to the git repository root.
        caller_state_dir: The caller's state directory for writing output.
    """

    worktree_key: str
    source: str
    git_root: Path
    caller_state_dir: Path


@dataclass(frozen=True)
class WorktreeStateDir:
    """A discovered state directory for a specific identity and worktree_key.

    Attributes:
        identity: The identity directory name.
        path: Absolute path to the state directory.
        has_logs: Whether ``background-tasks/logs/`` exists under this directory.
    """

    identity: str
    path: Path
    has_logs: bool


def resolve_analysis_context(
    *,
    issue_key: str | None = None,
    pr_id: int | None = None,
) -> AnalysisContext:
    """Resolve the analysis target from optional parameters.

    Args:
        issue_key: Optional issue key (e.g. ``"PROJECT-123"``).
        pr_id: Optional PR ID (e.g. ``42``).

    Returns:
        An ``AnalysisContext`` with the resolved worktree key and metadata.

    Raises:
        ValueError: If both ``issue_key`` and ``pr_id`` are provided, if
            ``issue_key`` is empty, or if no worktree key can be determined.
    """
    if issue_key is not None and pr_id is not None:
        msg = "--issue-key and --pr-id are mutually exclusive. Provide one or neither."
        raise ValueError(msg)

    if issue_key is not None:
        stripped = issue_key.strip()
        if not stripped:
            msg = "--issue-key value must not be empty."
            raise ValueError(msg)
        worktree_key = stripped
        source = "issue_key"
    elif pr_id is not None:
        worktree_key = f"PR{pr_id}"
        source = "pr_id"
    else:
        bootstrap = get_bootstrap_state()
        worktree_key = bootstrap.get("worktree_key", "")
        if not worktree_key:
            msg = (
                "No --issue-key or --pr-id provided and no worktree_key found "
                "in bootstrap. Set a worktree key via agdt-set or provide a parameter."
            )
            raise ValueError(msg)
        source = "bootstrap"

    git_root = _get_git_repo_root()
    if git_root is None:
        msg = "Not in a git repository. Cannot resolve analysis context."
        raise ValueError(msg)

    caller_state_dir = get_state_dir()

    return AnalysisContext(
        worktree_key=worktree_key,
        source=source,
        git_root=git_root,
        caller_state_dir=caller_state_dir,
    )


def list_worktree_state_dirs(
    git_root: Path,
    worktree_key: str,
) -> list[WorktreeStateDir]:
    """Scan identity directories for state dirs matching ``worktree_key``.

    Looks under ``.agdt/workflows/*/`` (excluding ``_unscoped``) for directories
    named ``worktree_key`` that contain workflow state.

    Args:
        git_root: Path to the git repository root.
        worktree_key: The target worktree key to search for.

    Returns:
        A sorted list of ``WorktreeStateDir`` instances (sorted by identity name
        for determinism).
    """
    workflows_dir = git_root / ".agdt" / "workflows"
    if not workflows_dir.is_dir():
        return []

    results: list[WorktreeStateDir] = []

    try:
        entries = sorted(workflows_dir.iterdir())
    except PermissionError:
        return []

    for identity_dir in entries:
        if not identity_dir.is_dir():
            continue
        if identity_dir.name == "_unscoped":
            continue
        if not is_safe_dir_segment(identity_dir.name):
            continue

        state_dir = identity_dir / worktree_key
        if not state_dir.is_dir():
            continue

        logs_dir = state_dir / "background-tasks" / "logs"
        has_logs = logs_dir.is_dir()

        results.append(
            WorktreeStateDir(
                identity=identity_dir.name,
                path=state_dir,
                has_logs=has_logs,
            )
        )

    return results
