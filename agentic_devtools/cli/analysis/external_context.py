"""External worktree context collection for workflow analysis.

This module discovers external git worktrees and collects log evidence
from them in read-only mode. It never writes, creates, or modifies
anything in external worktree paths.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ExternalLogEvidence:
    """Log evidence from an external worktree.

    Attributes:
        worktree_path: Path to the external worktree.
        identity: Identity directory name where the log was found.
        log_file: Absolute path to the log file.
        excerpt: Last lines of the log file (truncated to 500 lines).
        timestamp: File modification time as ISO-8601 string.
    """

    worktree_path: str
    identity: str
    log_file: str
    excerpt: str
    timestamp: str


@dataclass(frozen=True)
class ExternalContext:
    """Context collected from external worktrees.

    Attributes:
        worktrees_scanned: Paths of external worktrees that were scanned.
        log_evidence: Log evidence collected from external worktrees.
        identities_scanned: Identity directory names that were scanned.
    """

    worktrees_scanned: list[str] = field(default_factory=list)
    log_evidence: list[ExternalLogEvidence] = field(default_factory=list)
    identities_scanned: list[str] = field(default_factory=list)


_MAX_LOG_LINES = 500


def _discover_worktrees(git_root: Path) -> list[str]:
    """Discover git worktrees via ``git worktree list --porcelain``.

    Returns a list of worktree paths (excluding the main worktree at
    ``git_root``).
    """
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(git_root),
        )
    except (FileNotFoundError, OSError):
        return []

    if result.returncode != 0:
        return []

    worktrees: list[str] = []
    main_path = str(git_root.resolve())
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            wt_path = line[len("worktree ") :].strip()
            if not wt_path:
                continue
            # Normalize relative paths against git_root (not CWD) to ensure
            # correct main-worktree filtering regardless of process CWD.
            wt = Path(wt_path)
            if not wt.is_absolute():
                wt = (git_root / wt).resolve()
            else:
                wt = wt.resolve()
            if str(wt) != main_path:
                worktrees.append(str(wt))

    return sorted(worktrees)


def _read_log_excerpt(log_path: Path) -> str:
    """Read the last ``_MAX_LOG_LINES`` lines of a log file.

    Uses a streaming bounded deque so memory stays proportional to
    the excerpt size, not the full file size. Prepends a truncation
    header when the file has more lines than the limit.
    """
    import collections

    total_lines = 0
    tail: collections.deque[str] = collections.deque(maxlen=_MAX_LOG_LINES)
    try:
        with log_path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                total_lines += 1
                tail.append(line)
    except (OSError, UnicodeDecodeError):
        return ""

    lines = [line.rstrip("\r\n") for line in tail]

    if total_lines > _MAX_LOG_LINES:
        truncated_count = total_lines - _MAX_LOG_LINES
        return f"[…truncated {truncated_count} lines…]\n" + "\n".join(lines)

    return "\n".join(lines)


def collect_external_context(
    git_root: Path,
    worktree_key: str,
    *,
    static_only: bool = False,
) -> ExternalContext | None:
    """Collect log evidence from external worktrees (read-only).

    Args:
        git_root: Path to the git repository root.
        worktree_key: The target worktree key.
        static_only: If ``True``, skip external worktree scanning and return ``None``.

    Returns:
        An ``ExternalContext`` when external worktrees with ``.agdt/workflows/``
        directories are found (even if no matching log evidence exists), or
        ``None`` when ``static_only`` is set or no external worktrees have
        workflow directories.

    Raises:
        ValueError: If ``worktree_key`` is not a safe directory segment.
    """
    if static_only:
        return None

    external_paths = _discover_worktrees(git_root)
    if not external_paths:
        return None

    from agentic_devtools.state import is_safe_dir_segment

    # Validate worktree_key before using it in path construction
    # to prevent path traversal.
    if not is_safe_dir_segment(worktree_key):
        msg = f"worktree_key {worktree_key!r} is not a safe directory segment."
        raise ValueError(msg)

    all_evidence: list[ExternalLogEvidence] = []
    identities_seen: set[str] = set()
    worktrees_scanned: list[str] = []

    for wt_path_str in external_paths:
        wt_path = Path(wt_path_str)
        workflows_dir = wt_path / ".agdt" / "workflows"
        if not workflows_dir.is_dir():
            continue

        # Track worktree as scanned as soon as it has a workflows dir,
        # regardless of whether matching log evidence is found.
        worktrees_scanned.append(wt_path_str)

        try:
            identity_dirs = sorted(workflows_dir.iterdir())
        except (PermissionError, OSError):
            continue

        for identity_dir in identity_dirs:
            if not identity_dir.is_dir():
                continue
            if identity_dir.name == "_unscoped":
                continue
            if not is_safe_dir_segment(identity_dir.name):
                continue

            # Track identity as soon as it's eligible for scanning,
            # regardless of whether log evidence is found.
            identities_seen.add(identity_dir.name)

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

                try:
                    mtime = os.path.getmtime(log_file)
                except OSError:
                    continue

                from datetime import datetime, timezone

                timestamp = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
                excerpt = _read_log_excerpt(log_file)

                all_evidence.append(
                    ExternalLogEvidence(
                        worktree_path=wt_path_str,
                        identity=identity_dir.name,
                        log_file=str(log_file),
                        excerpt=excerpt,
                        timestamp=timestamp,
                    )
                )

    if not worktrees_scanned:
        return None

    return ExternalContext(
        worktrees_scanned=sorted(worktrees_scanned),
        log_evidence=all_evidence,
        identities_scanned=sorted(identities_seen),
    )


def build_external_context_field(
    external_ctx: ExternalContext | None,
) -> dict | None:
    """Convert ``ExternalContext`` to a JSON-serializable dict.

    Args:
        external_ctx: The external context, or ``None``.

    Returns:
        A dict suitable for inclusion in the JSON output schema, or ``None``
        when ``external_ctx`` is ``None``. The caller serializes ``None`` as
        ``"external_context": null`` in the JSON output.
    """
    if external_ctx is None:
        return None

    return {
        "worktrees_scanned": external_ctx.worktrees_scanned,
        "log_evidence": [
            {
                "worktree_path": ev.worktree_path,
                "identity": ev.identity,
                "log_file": ev.log_file,
                "excerpt": ev.excerpt,
                "timestamp": ev.timestamp,
            }
            for ev in external_ctx.log_evidence
        ],
        "identities_scanned": external_ctx.identities_scanned,
    }
