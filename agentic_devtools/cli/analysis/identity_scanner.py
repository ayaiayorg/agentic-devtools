"""Multi-identity log scanning for workflow analysis.

This module scans all identity directories under ``.agdt/workflows/`` for
log evidence related to a target worktree key, attributing each entry with
the identity directory name.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from agentic_devtools.state import IDENTITY_OWNER_FILENAME, is_safe_dir_segment


@dataclass(frozen=True)
class IdentityDir:
    """An identity directory under ``.agdt/workflows/``.

    Attributes:
        name: The directory name (identity segment).
        path: Absolute path to the identity directory.
        owner_email: Email from ``.identity-owner`` file, or ``None``.
    """

    name: str
    path: Path
    owner_email: str | None


@dataclass(frozen=True)
class LogEvidence:
    """A log file discovered during identity scanning.

    Attributes:
        identity: The identity directory name where the log was found.
        path: Absolute path to the log file.
        modified_time: File modification time as ISO-8601 string.
    """

    identity: str
    path: Path
    modified_time: str


def list_identity_directories(git_root: Path) -> list[IdentityDir]:
    """List all identity directories under ``.agdt/workflows/``.

    Excludes ``_unscoped`` and directories with unsafe names. Reads
    ``.identity-owner`` files for owner email attribution.

    Args:
        git_root: Path to the git repository root.

    Returns:
        A sorted list of ``IdentityDir`` instances (sorted by name for
        determinism).
    """
    workflows_dir = git_root / ".agdt" / "workflows"
    if not workflows_dir.is_dir():
        return []

    results: list[IdentityDir] = []

    try:
        entries = sorted(workflows_dir.iterdir())
    except (PermissionError, OSError):
        return []

    for identity_dir in entries:
        if not identity_dir.is_dir():
            continue
        if identity_dir.name == "_unscoped":
            continue
        if not is_safe_dir_segment(identity_dir.name):
            continue

        owner_email: str | None = None
        owner_file = identity_dir / IDENTITY_OWNER_FILENAME
        try:
            if owner_file.is_file():
                content = owner_file.read_text(encoding="utf-8").strip()
                if content:
                    owner_email = content
        except (OSError, UnicodeDecodeError):
            pass

        results.append(
            IdentityDir(
                name=identity_dir.name,
                path=identity_dir,
                owner_email=owner_email,
            )
        )

    return results


def scan_identity_logs(
    git_root: Path,
    worktree_key: str,
    workflow_name: str | None = None,
) -> list[LogEvidence]:
    """Scan all identity directories for log files matching the worktree key.

    Iterates all identity directories under ``.agdt/workflows/`` (skipping
    ``_unscoped``), looks for ``{worktree_key}/background-tasks/logs/``
    in each, and optionally filters logs whose filename contains
    ``workflow_name``.

    Args:
        git_root: Path to the git repository root.
        worktree_key: The target worktree key.
        workflow_name: Optional workflow name to filter log filenames.

    Returns:
        A sorted list of ``LogEvidence`` instances (sorted by identity then
        path for determinism).
    """
    # Validate worktree_key before using it in path construction
    # to prevent path traversal.
    if not is_safe_dir_segment(worktree_key):
        msg = f"worktree_key {worktree_key!r} is not a safe directory segment."
        raise ValueError(msg)

    workflows_dir = git_root / ".agdt" / "workflows"
    if not workflows_dir.is_dir():
        return []

    results: list[LogEvidence] = []

    try:
        identity_dirs = sorted(workflows_dir.iterdir())
    except (PermissionError, OSError):
        return []

    for identity_dir in identity_dirs:
        if not identity_dir.is_dir():
            continue
        if identity_dir.name == "_unscoped":
            continue
        if not is_safe_dir_segment(identity_dir.name):
            continue

        logs_dir = identity_dir / worktree_key / "background-tasks" / "logs"
        if not logs_dir.is_dir():
            continue

        try:
            log_files = sorted(logs_dir.iterdir())
        except (PermissionError, OSError):
            continue

        for log_file in log_files:
            if not log_file.is_file():
                continue

            if workflow_name is not None:
                # Normalize workflow name for matching: convert kebab-case to
                # underscore (log filenames use underscores)
                normalized = workflow_name.replace("-", "_")
                if normalized not in log_file.name and workflow_name not in log_file.name:
                    continue

            try:
                mtime = os.path.getmtime(log_file)
            except OSError:
                continue

            from datetime import datetime, timezone

            modified_time = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()

            results.append(
                LogEvidence(
                    identity=identity_dir.name,
                    path=log_file,
                    modified_time=modified_time,
                )
            )

    return results


def format_evidence_prefix(identity: str) -> str:
    """Return the attribution prefix for log evidence from an identity.

    Args:
        identity: The identity directory name.

    Returns:
        A string in the format ``[identity: {identity}]``.
    """
    return f"[identity: {identity}]"
