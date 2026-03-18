"""
Auto-start command for the Copilot CLI session in a VS Code worktree.

This module provides ``copilot_auto_start_cmd()``, which is invoked by the
``agdt-copilot-auto-start`` VS Code task.  It replaces the platform-specific
inline shell command previously embedded in ``.vscode/tasks.json``.

Responsibilities
----------------
1. Validate ``--worktree-path`` is an existing directory — exit 1 if not.
2. Check for the sentinel file — exit early (0) if already triggered.
3. Check copilot CLI availability — exit 1 if unavailable (before creating sentinel).
3b. Check ``agdt-advance-workflow`` reachability — exit 1 if not found on PATH.
4. Build copilot args — exit 1 if the prompt exceeds argv limits.
5. Create the sentinel file atomically (``O_CREAT|O_EXCL``) — exit 0 without
   starting a session if another process already created it (race-free guard).
6. Run the Copilot CLI command — on OSError or KeyboardInterrupt remove
   sentinel and exit (1 for OSError, 130 for KeyboardInterrupt).
7. On failure: remove the sentinel file and exit with the copilot exit code.
8. On success: perform best-effort cleanup of the auto-start task from
   ``.vscode/tasks.json``, then exit 0.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

from agentic_devtools.cli.copilot.session import (
    build_copilot_args,
    is_gh_copilot_available,
)
from agentic_devtools.cli.vscode_tasks import remove_auto_start_task

_DEFAULT_TASK_LABEL = "agdt-copilot-auto-start"
_SENTINEL_REL = os.path.join(".agdt", ".copilot-auto-start-triggered")


def _cleanup_auto_start_task(
    worktree_path: str,
    task_label: str,
    created_new: bool,
) -> None:
    """Best-effort removal of the auto-start task from ``.vscode/tasks.json``.

    Delegates to :func:`~agentic_devtools.cli.vscode_tasks.remove_auto_start_task`.

    All errors are silently caught — cleanup failure must never change the
    caller's exit code.

    Args:
        worktree_path: Absolute path to the worktree directory.
        task_label: The label identifying the task to remove.
        created_new: ``True`` when ``tasks.json`` was created by the injection
            (did not exist beforehand).  When ``True`` and no tasks remain after
            removal the file is deleted and ``.vscode/`` is removed if empty —
            unless other top-level keys (e.g. ``inputs``/``options``) are
            present, in which case the file is rewritten with an empty tasks
            array to preserve those keys.  When ``False`` the file is always
            rewritten.
    """
    vscode_dir = os.path.join(worktree_path, ".vscode")
    tasks_path = os.path.join(vscode_dir, "tasks.json")
    try:
        remove_auto_start_task(
            tasks_path,
            vscode_dir,
            task_label,
            delete_if_empty=created_new,
        )
    except Exception:
        # Best-effort cleanup: any failure must be silently ignored so it cannot
        # affect the caller's exit code.
        pass


def copilot_auto_start_cmd(argv: list[str] | None = None) -> None:
    """Entry point for the ``agdt-copilot-auto-start`` CLI command.

    Parses ``sys.argv[1:]`` (or *argv* when provided) and executes the
    auto-start flow:

    1. Validate ``--worktree-path`` is an existing directory; exit 1 if not.
    2. Sentinel check — exit 0 immediately if already triggered (best-effort
       stale task cleanup first).
    3. Pre-flight: check copilot CLI availability; exit 1 if not available.
    3b. Pre-flight: check ``agdt-advance-workflow`` reachability; exit 1 if not found.
    4. Build copilot args; exit 1 if prompt exceeds argv limits.
    5. Create sentinel file atomically (``O_CREAT|O_EXCL``); exit 0 without
       running if another concurrent invocation already created it.
    6. Run copilot CLI; on OSError remove sentinel and exit 1; on
       KeyboardInterrupt remove sentinel and exit 130.
    7. On failure: remove sentinel, exit with copilot exit code.
    8. On success: clean up the task from ``tasks.json``, exit 0.
    """
    parser = argparse.ArgumentParser(
        prog="agdt-copilot-auto-start",
        description="Run the Copilot auto-start session inside a VS Code worktree.",
    )
    parser.add_argument(
        "--worktree-path",
        required=True,
        help="Absolute path to the worktree directory.",
    )
    parser.add_argument(
        "--start-prompt",
        required=True,
        help="The prompt text to pass to the Copilot binary.",
    )
    parser.add_argument(
        "--task-label",
        default=_DEFAULT_TASK_LABEL,
        help="The label identifying the task in tasks.json (default: %(default)s).",
    )
    parser.add_argument(
        "--created-new",
        action="store_true",
        help="When set, cleanup deletes tasks.json (and .vscode/ if empty) instead of rewriting when no tasks remain.",
    )

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    worktree_path: str = args.worktree_path
    start_prompt: str = args.start_prompt
    task_label: str = args.task_label
    created_new: bool = args.created_new

    # 1. Validate worktree_path before any filesystem writes.  An invalid path
    #    would cause confusing downstream errors (e.g. makedirs creating stray
    #    directories under an unexpected location, or misleading FileNotFoundError
    #    messages from subprocess.run when cwd doesn't exist).
    if not os.path.isdir(worktree_path):
        print(
            f"agdt-copilot-auto-start: error: worktree path does not exist or is not a directory: {worktree_path!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    sentinel_path = os.path.join(worktree_path, _SENTINEL_REL)

    # 2. Sentinel check — if already triggered, assume another process has
    #    already handled (or is currently handling) auto-start. Before
    #    exiting, attempt best-effort cleanup of any stale auto-start task.
    if os.path.exists(sentinel_path):
        _cleanup_auto_start_task(worktree_path, task_label, created_new)
        sys.exit(0)

    # 3. Pre-flight: bail out early if the copilot CLI is not available.
    #    Running this check before creating the sentinel prevents an unavailable
    #    CLI from leaving a stale sentinel that would suppress all future attempts.
    if not is_gh_copilot_available():
        print(
            "agdt-copilot-auto-start: error: copilot CLI not available; cannot start session.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 3b. Pre-flight: bail out early if agdt-* CLI commands are not on PATH.
    #     This check prevents a confusing "command not found" error inside the
    #     Copilot session after it has already started.
    if not shutil.which("agdt-advance-workflow"):
        print(
            "agdt-copilot-auto-start: error: agdt-advance-workflow not found on PATH; "
            "agentic-devtools CLI commands are not available. "
            "Ensure agentic-devtools is installed and the Scripts directory is on your PATH. "
            "Install options: 'pip install agentic-devtools', 'pipx install agentic-devtools', "
            "or see the managed install at $HOME/.agdt/bin (or %USERPROFILE%\\.agdt\\bin on Windows).",
            file=sys.stderr,
        )
        sys.exit(1)

    # 4. Build copilot args — bail out early if the prompt exceeds argv length limits.
    copilot_args = build_copilot_args(start_prompt, interactive=True)
    if copilot_args is None:
        print(
            "agdt-copilot-auto-start: error: start prompt is too large for Copilot CLI argv limits; "
            "cannot auto-start session. Try shortening the prompt or starting Copilot manually.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 5. Create sentinel file atomically using O_CREAT|O_EXCL so that two
    #    concurrent invocations (e.g. VS Code opening the same worktree twice
    #    in quick succession) cannot both proceed past this point.  If another
    #    process already created the sentinel we treat it as "already triggered"
    #    and exit cleanly without starting a duplicate Copilot session.
    try:
        os.makedirs(os.path.dirname(sentinel_path), exist_ok=True)
        fd = os.open(sentinel_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except FileExistsError:
        # Another concurrent invocation created the sentinel first — treat as
        # "already triggered" and exit without starting a duplicate session.
        sys.exit(0)
    except OSError as exc:
        print(
            f"agdt-copilot-auto-start: error: could not create sentinel file: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    # 6. Run the copilot command (interactive — inherit VS Code terminal).
    #    Wrapped in try/except to handle the TOCTOU race where the binary could
    #    disappear from PATH between the availability check and execution, and to
    #    ensure the sentinel is cleaned up if the user interrupts with Ctrl+C.
    #
    #    FileNotFoundError can arise from two distinct causes:
    #    a) The Copilot CLI binary is missing from PATH.
    #    b) The worktree directory no longer exists (cwd not found).
    #    We disambiguate by re-checking the worktree directory so users get a
    #    targeted message rather than a confusing "executable not found" report
    #    for a missing cwd.
    try:
        result = subprocess.run(copilot_args, cwd=worktree_path)  # noqa: S603
        exit_code = result.returncode
    except FileNotFoundError as exc:
        if not os.path.isdir(worktree_path):
            print(
                f"agdt-copilot-auto-start: error: worktree path no longer exists: {worktree_path!r}",
                file=sys.stderr,
            )
        else:
            print(
                f"agdt-copilot-auto-start: error: Copilot CLI executable not found: {exc}",
                file=sys.stderr,
            )
        try:
            os.remove(sentinel_path)
        except OSError:
            pass
        sys.exit(1)
    except OSError as exc:
        print(
            f"agdt-copilot-auto-start: error: failed to run Copilot CLI (worktree path: {worktree_path}): {exc}",
            file=sys.stderr,
        )
        try:
            os.remove(sentinel_path)
        except OSError:
            pass
        sys.exit(1)
    except KeyboardInterrupt:
        # User interrupted (Ctrl+C) — remove sentinel so next folderOpen retries.
        try:
            os.remove(sentinel_path)
        except OSError:
            pass
        sys.exit(130)

    # 7a. On failure: remove sentinel so next folderOpen retries.
    if exit_code != 0:
        try:
            os.remove(sentinel_path)
        except OSError:
            pass
        sys.exit(exit_code)

    # 7b. On success: best-effort cleanup of the task from tasks.json.
    _cleanup_auto_start_task(worktree_path, task_label, created_new)
    sys.exit(0)
