"""Git tool adapter functions.

Stateless, typed functions for Git operations. Each function wraps the
lower-level operations in ``agentic_devtools.cli.git.operations`` and
returns structured ``TypedDict`` results instead of printing to stdout.
"""

from __future__ import annotations

import contextlib
import io

from typing_extensions import TypedDict

# ---------------------------------------------------------------------------
# Result TypedDicts
# ---------------------------------------------------------------------------


class GitOperationResult(TypedDict):
    """Result of a single git operation."""

    success: bool
    message: str


class SaveWorkResult(TypedDict):
    """Result of a composite save-work operation."""

    success: bool
    message: str
    operations: list[str]


class RecentChangesResult(TypedDict):
    """Result of querying recent git changes."""

    commits: list[dict]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _capture(func, *args, **kwargs) -> str:  # type: ignore[no-untyped-def]
    """Call *func* and capture whatever it prints to stdout.

    If *func* raises, the exception propagates and any captured output
    is discarded.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        func(*args, **kwargs)
    return buf.getvalue()


def _run_op(func, *args, **kwargs) -> GitOperationResult:  # type: ignore[no-untyped-def]
    """Run a git operation function, capturing stdout/stderr into a result dict.

    Stderr is captured so that when underlying git helpers print diagnostics
    (e.g. via ``run_git``) before raising ``SystemExit``, the error details
    are preserved in the result message rather than lost.
    """
    err_buf = io.StringIO()
    try:
        with contextlib.redirect_stderr(err_buf):
            output = _capture(func, *args, **kwargs)
        stderr_text = err_buf.getvalue().strip()
        message = output.strip()
        if stderr_text:
            message = f"{message}\n{stderr_text}" if message else stderr_text
        return GitOperationResult(success=True, message=message)
    except SystemExit as exc:
        code = exc.code if exc.code is not None else 1
        stderr_text = err_buf.getvalue().strip()
        detail = stderr_text if stderr_text else f"exit code {code}"
        return GitOperationResult(
            success=False,
            message=f"Operation failed: {detail}",
        )
    except Exception as exc:  # noqa: BLE001
        return GitOperationResult(success=False, message=str(exc))


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------


def stage_changes(dry_run: bool = False) -> GitOperationResult:
    """Stage all changes (``git add .``).

    Args:
        dry_run: Preview without executing.

    Returns:
        A :class:`GitOperationResult`.
    """
    from agentic_devtools.cli.git.operations import stage_changes as _stage_changes

    return _run_op(_stage_changes, dry_run)


def create_commit(message: str, dry_run: bool = False) -> GitOperationResult:
    """Create a new commit with the given message.

    Args:
        message: Commit message.
        dry_run: Preview without executing.

    Returns:
        A :class:`GitOperationResult`.
    """
    from agentic_devtools.cli.git.operations import create_commit as _create_commit

    return _run_op(_create_commit, message, dry_run)


def amend_commit(message: str, dry_run: bool = False) -> GitOperationResult:
    """Amend the current commit with a new message.

    Args:
        message: New commit message.
        dry_run: Preview without executing.

    Returns:
        A :class:`GitOperationResult`.
    """
    from agentic_devtools.cli.git.operations import amend_commit as _amend_commit

    return _run_op(_amend_commit, message, dry_run)


def push(dry_run: bool = False) -> GitOperationResult:
    """Push to remote (regular push).

    Args:
        dry_run: Preview without executing.

    Returns:
        A :class:`GitOperationResult`.
    """
    from agentic_devtools.cli.git.operations import push as _push

    return _run_op(_push, dry_run)


def force_push(dry_run: bool = False) -> GitOperationResult:
    """Force push with lease.

    Args:
        dry_run: Preview without executing.

    Returns:
        A :class:`GitOperationResult`.
    """
    from agentic_devtools.cli.git.operations import force_push as _force_push

    return _run_op(_force_push, dry_run)


def publish_branch(dry_run: bool = False) -> GitOperationResult:
    """Push and set upstream for the current branch.

    Args:
        dry_run: Preview without executing.

    Returns:
        A :class:`GitOperationResult`.
    """
    from agentic_devtools.cli.git.operations import publish_branch as _publish_branch

    return _run_op(_publish_branch, dry_run)


def save_work(
    commit_message: str,
    amend: bool = False,
    skip_stage: bool = False,
    skip_push: bool = False,
    dry_run: bool = False,
) -> SaveWorkResult:
    """Composite operation: stage → commit/amend → push/force-push.

    This is the tool-layer equivalent of the CLI ``commit_cmd`` workflow,
    without rebase, workflow advancement, or checklist logic.

    Args:
        commit_message: The commit message.
        amend: If *True*, amend the existing commit instead of creating a new one.
        skip_stage: If *True*, skip the staging step.
        skip_push: If *True*, skip the push step.
        dry_run: If *True*, preview operations without executing.

    Returns:
        A :class:`SaveWorkResult` listing the operations performed.
    """
    operations: list[str] = []
    messages: list[str] = []

    # Stage
    if not skip_stage:
        result = stage_changes(dry_run=dry_run)
        operations.append("stage_changes")
        messages.append(result["message"])
        if not result["success"]:
            return SaveWorkResult(
                success=False,
                message="\n".join(messages),
                operations=operations,
            )

    # Commit / amend
    if amend:
        result = amend_commit(commit_message, dry_run=dry_run)
        operations.append("amend_commit")
    else:
        result = create_commit(commit_message, dry_run=dry_run)
        operations.append("create_commit")
    messages.append(result["message"])
    if not result["success"]:
        return SaveWorkResult(
            success=False,
            message="\n".join(messages),
            operations=operations,
        )

    # Push
    if not skip_push:
        if amend:
            result = force_push(dry_run=dry_run)
            operations.append("force_push")
        else:
            result = push(dry_run=dry_run)
            operations.append("push")
        messages.append(result["message"])
        if not result["success"]:
            return SaveWorkResult(
                success=False,
                message="\n".join(messages),
                operations=operations,
            )

    return SaveWorkResult(
        success=True,
        message="\n".join(messages),
        operations=operations,
    )


def get_recent_changes(num_commits: int = 10) -> RecentChangesResult:
    """Return recent commits from the current branch.

    Args:
        num_commits: Maximum number of commits to return.

    Returns:
        A :class:`RecentChangesResult` with a list of commit dicts.
    """
    from agentic_devtools.cli.git.core import run_git

    # Use ASCII Unit Separator (\x1f) instead of "|" to avoid corruption
    # when commit subjects contain pipe characters.
    _SEP = "\x1f"

    result = run_git(
        "log",
        f"--max-count={num_commits}",
        "--format=%H%x1f%s%x1f%an%x1f%ai",
        check=False,
    )

    commits: list[dict] = []
    if result.returncode == 0 and result.stdout.strip():
        for line in result.stdout.strip().splitlines():
            parts = line.split(_SEP, 3)
            if len(parts) == 4:
                commits.append(
                    {
                        "sha": parts[0],
                        "message": parts[1],
                        "author": parts[2],
                        "date": parts[3],
                    }
                )

    return RecentChangesResult(commits=commits)
