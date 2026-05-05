"""
Auto-start command for the Copilot CLI session in a VS Code worktree.

This module provides ``copilot_auto_start_cmd()``, which is invoked by the
``agdt-copilot-auto-start`` VS Code task.  It replaces the platform-specific
inline shell command previously embedded in ``.vscode/tasks.json``.

Responsibilities
----------------
1. Validate ``--worktree-path`` is an existing directory — exit 1 if not.
2. Check whether the current ``--run-id`` has already been triggered (via
   ``copilot.auto_start_triggered_runs`` in the workflow state) — exit
   early (0) if so.
3. Check copilot CLI availability — exit 1 if unavailable (before marking).
3b. Check ``agdt-advance-workflow`` reachability — exit 1 if not found on PATH.
4. Build copilot args — exit 1 if the prompt exceeds argv limits.
5. Atomically mark the run ID as triggered in state (using
   ``locked_state_file``) — exit 0 without starting a session if another
   concurrent process already marked it (race-free guard).
6. Run the Copilot CLI command — on OSError or KeyboardInterrupt unmark the
   run ID and exit (1 for OSError, 130 for KeyboardInterrupt).
7. On failure: unmark the run ID and exit with the copilot exit code.
8. On success: perform best-effort cleanup of the auto-start task from
   ``.vscode/tasks.json``, then exit 0.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from agentic_devtools.cli.copilot.session import (
    build_copilot_args,
    get_default_copilot_model,
    is_gh_copilot_available,
)
from agentic_devtools.cli.vscode_tasks import remove_auto_start_task
from agentic_devtools.file_locking import FileLockError, locked_state_file
from agentic_devtools.state import get_state_file_path

_DEFAULT_TASK_LABEL = "agdt-copilot-auto-start"
_STATE_KEY = "copilot"
_TRIGGERED_RUNS_KEY = "auto_start_triggered_runs"
_MODEL_KEY = "model_id"

# Retry constants for transient Windows file-lock errors (WinError 32).
_RETRY_MAX_ATTEMPTS = 5  # retries (6 total tries)
_RETRY_INITIAL_DELAY_S = 0.5  # first backoff delay in seconds
_RETRY_BACKOFF_FACTOR = 2.0  # doubling
_RETRY_MAX_DELAY_S = 4.0  # cap per delay in seconds


def _read_model_from_state(state_file_path: Path) -> str | None:
    """Read ``copilot.model_id`` from the state file.

    Returns the model ID string if present and non-empty, ``None`` otherwise.
    Swallows all errors so callers can safely fall back to a default.
    """
    try:
        with locked_state_file(state_file_path) as fh:
            content = fh.read()
            state = json.loads(content) if content.strip() else {}
            if not isinstance(state, dict):
                return None
            copilot = state.get(_STATE_KEY, {})
            if not isinstance(copilot, dict):
                return None
            model = copilot.get(_MODEL_KEY)
            if isinstance(model, str) and model.strip():
                return model.strip()
            return None
    except (FileLockError, json.JSONDecodeError, OSError, TypeError, AttributeError):
        return None


def _is_run_triggered(state_file_path: Path, run_id: str) -> bool:
    """Check whether *run_id* has already been auto-triggered.

    Reads ``copilot.auto_start_triggered_runs`` from the state file under an
    exclusive lock and returns ``True`` when *run_id* is present.  Returns
    ``False`` on any error (missing file, corrupt JSON, lock timeout).
    """
    try:
        with locked_state_file(state_file_path) as fh:
            content = fh.read()
            state = json.loads(content) if content.strip() else {}
            if not isinstance(state, dict):
                state = {}
            copilot = state.get(_STATE_KEY, {})
            if not isinstance(copilot, dict):
                copilot = {}
            triggered = copilot.get(_TRIGGERED_RUNS_KEY, [])
            return isinstance(triggered, list) and run_id in triggered
    except (FileLockError, json.JSONDecodeError, OSError, TypeError, AttributeError):
        return False


def _mark_run_triggered(state_file_path: Path, run_id: str) -> bool:
    """Atomically mark *run_id* as triggered in the state file.

    Uses ``locked_state_file`` for an exclusive-lock read-check-write cycle.
    Returns ``True`` if *run_id* was newly added, ``False`` if the run ID was
    already present (concurrent race lost).

    Raises ``FileLockError`` if the lock cannot be acquired.
    """
    with locked_state_file(state_file_path) as fh:
        content = fh.read()
        try:
            state = json.loads(content) if content.strip() else {}
        except json.JSONDecodeError:
            # Treat corrupt state as empty to avoid crashing the auto-start task.
            state = {}

        if not isinstance(state, dict):
            state = {}

        copilot = state.get(_STATE_KEY)
        if not isinstance(copilot, dict):
            copilot = {}
            state[_STATE_KEY] = copilot

        triggered = copilot.get(_TRIGGERED_RUNS_KEY, [])
        if not isinstance(triggered, list):
            # Normalise unexpected types to an empty list.
            triggered = []
        copilot[_TRIGGERED_RUNS_KEY] = triggered

        if run_id in triggered:
            return False  # another process won the race

        triggered.append(run_id)

        fh.seek(0)
        fh.write(json.dumps(state, indent=2, ensure_ascii=False))
        fh.truncate()
        return True


def _unmark_run_triggered(state_file_path: Path, run_id: str) -> None:
    """Best-effort removal of *run_id* from the triggered-runs list in state.

    Logs (but otherwise ignores) all errors (lock timeout, corrupt JSON, etc.)
    so the caller's exit code is never affected.
    """
    try:
        with locked_state_file(state_file_path) as fh:
            content = fh.read()
            try:
                state = json.loads(content) if content.strip() else {}
            except json.JSONDecodeError:
                # Treat corrupt state as empty to avoid crashing the auto-start task.
                state = {}

            if not isinstance(state, dict):
                state = {}

            copilot = state.get(_STATE_KEY)
            if not isinstance(copilot, dict):
                copilot = {}
                state[_STATE_KEY] = copilot

            triggered = copilot.get(_TRIGGERED_RUNS_KEY, [])
            if not isinstance(triggered, list):
                # Normalise unexpected types to an empty list.
                triggered = []
            copilot[_TRIGGERED_RUNS_KEY] = triggered

            if run_id in triggered:
                triggered.remove(run_id)

                fh.seek(0)
                fh.write(json.dumps(state, indent=2, ensure_ascii=False))
                fh.truncate()
    except Exception as exc:
        print(
            f"[agentic-devtools] Warning: failed to unmark Copilot auto-start "
            f"run_id={run_id!r} in state file {state_file_path!s}: {exc!r}",
            file=sys.stderr,
        )


def _is_retryable_win_error(exc: OSError) -> bool:
    """Return ``True`` if *exc* is a Windows ``ERROR_SHARING_VIOLATION``.

    On Windows, ``OSError`` instances carry a ``winerror`` attribute with the
    native Windows error code.  Code 32 (``ERROR_SHARING_VIOLATION``) indicates
    a transient file lock held by another process (e.g., antivirus, indexer,
    VS Code).

    On non-Windows platforms, ``OSError`` instances lack the ``winerror``
    attribute entirely, so this function safely returns ``False``.
    """
    return getattr(exc, "winerror", None) == 32


def _run_copilot_with_retry(
    copilot_args: list[str],
    cwd: str,
) -> subprocess.CompletedProcess:
    """Run the Copilot CLI with retry logic for transient Windows file locks.

    Wraps ``subprocess.run`` with exponential backoff retries specifically for
    ``OSError`` with ``winerror == 32`` (Windows ``ERROR_SHARING_VIOLATION``).

    Non-retryable errors (``FileNotFoundError``, other ``OSError`` variants)
    are re-raised immediately without retry.

    Args:
        copilot_args: Command-line arguments for the Copilot CLI.
        cwd: Working directory for the subprocess.

    Returns:
        The ``CompletedProcess`` on success.

    Raises:
        FileNotFoundError: If the binary or cwd is missing (not retried).
        OSError: If a non-retryable OS error occurs, or if retries are
            exhausted for a retryable error.
        KeyboardInterrupt: If the user interrupts during a backoff sleep.
    """
    if _RETRY_MAX_ATTEMPTS < 0:
        raise ValueError(
            f"_RETRY_MAX_ATTEMPTS must be >= 0, got {_RETRY_MAX_ATTEMPTS}"
        )
    total_tries = _RETRY_MAX_ATTEMPTS + 1
    delay = _RETRY_INITIAL_DELAY_S

    for attempt in range(1, total_tries + 1):
        try:
            return subprocess.run(copilot_args, cwd=cwd)  # noqa: S603
        except FileNotFoundError:
            raise
        except OSError as exc:
            if not _is_retryable_win_error(exc):
                raise
            if attempt == total_tries:
                # Budget exhausted — log summary and re-raise.
                print(
                    f"agdt-copilot-auto-start: error: retry budget exhausted "
                    f"after {total_tries} attempts (winerror={getattr(exc, 'winerror', '?')}): {exc}",
                    file=sys.stderr,
                )
                raise
            # Log retry info and sleep with backoff.
            print(
                f"agdt-copilot-auto-start: warning: transient file lock "
                f"(attempt {attempt}/{total_tries}, winerror={getattr(exc, 'winerror', '?')}), "
                f"retrying in {delay:.1f}s: {exc}",
                file=sys.stderr,
            )
            time.sleep(delay)
            delay = min(delay * _RETRY_BACKOFF_FACTOR, _RETRY_MAX_DELAY_S)

    # Should never be reached given the validation above, but guard defensively.
    raise RuntimeError(  # pragma: no cover
        "_run_copilot_with_retry: loop completed without returning or raising"
    )


def _cleanup_auto_start_task(
    worktree_path: str,
    task_label: str,
    created_new: bool,
) -> None:
    """Best-effort removal of the auto-start task from ``.vscode/tasks.json``.

    Delegates to :func:`~agentic_devtools.cli.vscode_tasks.remove_auto_start_task`.

    Errors are caught so that cleanup failure never changes the caller's exit
    code.  Transient Windows file-lock errors (``winerror == 32``) emit a
    warning to stderr; all other errors are silently ignored.

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
    except OSError as exc:
        if _is_retryable_win_error(exc):
            print(
                f"agdt-copilot-auto-start: warning: cleanup encountered transient "
                f"file lock (winerror=32), skipping: {exc}",
                file=sys.stderr,
            )
        # Best-effort cleanup: any failure must not affect the caller's exit code.
    except Exception:
        # Best-effort cleanup: any failure must be silently ignored so it cannot
        # affect the caller's exit code.
        pass


def copilot_auto_start_cmd(argv: list[str] | None = None) -> None:
    """Entry point for the ``agdt-copilot-auto-start`` CLI command.

    Parses ``sys.argv[1:]`` (or *argv* when provided) and executes the
    auto-start flow:

    1. Validate ``--worktree-path`` is an existing directory; exit 1 if not.
    2. Run-ID check — exit 0 immediately if the run ID is already in
       ``copilot.auto_start_triggered_runs`` (best-effort stale task cleanup
       first).
    3. Pre-flight: check copilot CLI availability; exit 1 if not available.
    3b. Pre-flight: check ``agdt-advance-workflow`` reachability; exit 1 if not found.
    4. Build copilot args; exit 1 if prompt exceeds argv limits.
    5. Atomically mark the run ID as triggered in state; exit 0 without
       running if another concurrent invocation already marked it.
    6. Run copilot CLI; on OSError unmark run ID and exit 1; on
       KeyboardInterrupt unmark run ID and exit 130.
    7. On failure: unmark run ID, exit with copilot exit code.
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
        "--run-id",
        required=True,
        help="Unique run ID for this workflow invocation.",
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
    parser.add_argument(
        "--model",
        dest="model",
        default=None,
        help="Copilot model to use (e.g., gpt-4o). Forwarded to the Copilot CLI.",
    )

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    worktree_path: str = args.worktree_path
    start_prompt: str = args.start_prompt
    run_id: str = args.run_id
    task_label: str = args.task_label
    created_new: bool = args.created_new

    # Validate run_id is not empty or whitespace-only. While argparse enforces
    # presence of the argument, it does not prevent values like "" or "   ",
    # which would result in ambiguous entries in copilot.auto_start_triggered_runs.
    if not run_id.strip():
        print(
            "agdt-copilot-auto-start: error: --run-id must be a non-empty, non-whitespace value.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Normalize run_id after validation so all downstream uses (state keys,
    # comparisons, etc.) operate on a canonical, whitespace-trimmed value.
    run_id = run_id.strip()

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

    # Resolve the state file path in the context of the target worktree. This
    # ensures that multi-worktree state remains isolated even when this command
    # is invoked from a different CWD or with AGENTIC_DEVTOOLS_STATE_DIR set.
    original_cwd = os.getcwd()
    original_state_dir = os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR")
    original_legacy_state_dir = os.environ.get("AGDT_AI_HELPERS_STATE_DIR")
    os.environ.pop("AGENTIC_DEVTOOLS_STATE_DIR", None)
    os.environ.pop("AGDT_AI_HELPERS_STATE_DIR", None)
    try:
        try:
            os.chdir(worktree_path)
        except OSError as exc:
            print(
                f"agdt-copilot-auto-start: error: failed to change directory to worktree {worktree_path!r}: {exc}",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            state_file_path = get_state_file_path()
        except Exception as exc:  # pragma: no cover - defensive guardrail
            print(
                "agdt-copilot-auto-start: error: failed to resolve state file path "
                f"for worktree {worktree_path!r}: {exc}",
                file=sys.stderr,
            )
            sys.exit(1)

        # Resolve the default model while CWD is still set to the target
        # worktree so that .agdt/config/project.json is read from the
        # correct repository, not from wherever this command was invoked.
        worktree_default_model = get_default_copilot_model()
    finally:
        try:
            os.chdir(original_cwd)
        except OSError as exc:
            # Best-effort warning only; avoid masking earlier exit paths with a traceback.
            print(
                "agdt-copilot-auto-start: warning: failed to restore original working "
                f"directory {original_cwd!r}: {exc}",
                file=sys.stderr,
            )
        if original_state_dir is not None:
            os.environ["AGENTIC_DEVTOOLS_STATE_DIR"] = original_state_dir
        else:
            os.environ.pop("AGENTIC_DEVTOOLS_STATE_DIR", None)
        if original_legacy_state_dir is not None:
            os.environ["AGDT_AI_HELPERS_STATE_DIR"] = original_legacy_state_dir
        else:
            os.environ.pop("AGDT_AI_HELPERS_STATE_DIR", None)

    # 2. Run-ID check — if the current run ID has already been triggered,
    #    assume another process has already handled (or is currently handling)
    #    auto-start.  Before exiting, attempt best-effort cleanup of any stale
    #    auto-start task.
    if _is_run_triggered(state_file_path, run_id):
        _cleanup_auto_start_task(worktree_path, task_label, created_new)
        sys.exit(0)

    # 3. Pre-flight: bail out early if the copilot CLI is not available.
    #    Running this check before marking the run ID prevents an unavailable
    #    CLI from leaving a stale entry that would suppress all future attempts.
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

    # 3c. Resolve model: when --model is omitted (or whitespace-only), read
    #     copilot.model_id from the worktree state (set by the initiating
    #     workflow command).  Fall back to get_default_copilot_model() so
    #     auto-start sessions always use the repo-wide configured default
    #     rather than the Copilot binary's implicit default.
    # Normalize: strip whitespace; treat empty as "not provided" so the
    # fallback chain (state → default) is exercised.
    model = args.model.strip() if isinstance(args.model, str) else args.model
    if not model:
        try:
            state_model = _read_model_from_state(state_file_path)
            if state_model:
                model = state_model
        except Exception:
            pass
    if not model:
        model = worktree_default_model

    # 4. Build copilot args — bail out early if the prompt exceeds argv length limits.
    copilot_args = build_copilot_args(start_prompt, interactive=True, model=model)
    if copilot_args is None:
        print(
            "agdt-copilot-auto-start: error: start prompt is too large for Copilot CLI argv limits; "
            "cannot auto-start session. Try shortening the prompt or starting Copilot manually.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 5. Atomically mark the run ID as triggered using locked_state_file so
    #    that two concurrent invocations (e.g. VS Code opening the same
    #    worktree twice in quick succession) cannot both proceed past this
    #    point.  If another process already marked the run ID we treat it as
    #    "already triggered" and exit cleanly without starting a duplicate
    #    Copilot session.
    try:
        newly_marked = _mark_run_triggered(state_file_path, run_id)
    except FileLockError as exc:
        print(
            f"agdt-copilot-auto-start: error: could not acquire state file lock: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
    except OSError as exc:
        print(
            f"agdt-copilot-auto-start: error: could not update state file: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not newly_marked:
        # Another concurrent invocation marked the run ID first — treat as
        # "already triggered" and exit without starting a duplicate session.
        sys.exit(0)

    # 6. Run the copilot command (interactive — inherit VS Code terminal).
    #    Wrapped in try/except to handle the TOCTOU race where the binary could
    #    disappear from PATH between the availability check and execution, and to
    #    ensure the run ID is unmarked if the user interrupts with Ctrl+C.
    #
    #    FileNotFoundError can arise from two distinct causes:
    #    a) The Copilot CLI binary is missing from PATH.
    #    b) The worktree directory no longer exists (cwd not found).
    #    We disambiguate by re-checking the worktree directory so users get a
    #    targeted message rather than a confusing "executable not found" report
    #    for a missing cwd.
    try:
        result = _run_copilot_with_retry(copilot_args, worktree_path)
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
        _unmark_run_triggered(state_file_path, run_id)
        sys.exit(1)
    except OSError as exc:
        print(
            f"agdt-copilot-auto-start: error: failed to run Copilot CLI (worktree path: {worktree_path}): {exc}",
            file=sys.stderr,
        )
        _unmark_run_triggered(state_file_path, run_id)
        sys.exit(1)
    except KeyboardInterrupt:
        # User interrupted (Ctrl+C) — unmark run ID so next folderOpen retries.
        _unmark_run_triggered(state_file_path, run_id)
        sys.exit(130)

    # 7a. On failure: unmark run ID so next folderOpen retries.
    if exit_code != 0:
        _unmark_run_triggered(state_file_path, run_id)
        sys.exit(exit_code)

    # 7b. On success: best-effort cleanup of the task from tasks.json
    #     and the pending auto-start marker file.
    _cleanup_auto_start_task(worktree_path, task_label, created_new)
    from agentic_devtools.cli.workflows.worktree_setup import _cleanup_pending_auto_start_marker

    _cleanup_pending_auto_start_marker(worktree_path)
    sys.exit(0)


def retry_autostart_cmd(argv: list[str] | None = None) -> None:
    """Entry point for the ``agdt-retry-autostart`` CLI command.

    Reads the ``pending-auto-start.json`` marker file from the target
    worktree's ``.vscode/`` directory and re-invokes
    :func:`copilot_auto_start_cmd` with the stored parameters, providing
    a simple single-command retry path when the primary autostart
    mechanisms fail.

    Steps
    -----
    1. Parse ``--worktree-path`` (default: CWD) and ``--force``.
    2. Read and validate ``<worktree_path>/.vscode/pending-auto-start.json``.
    3. Unless ``--force``, check the marker's ``run_id`` against the
       current ``agdt_run_id`` in state; exit 1 on mismatch.
    4. Call ``_unmark_run_triggered`` to clear the deduplication guard.
    5. Delegate to ``copilot_auto_start_cmd`` with the stored parameters.
    """
    from agentic_devtools.cli.workflows.worktree_setup import (
        _PENDING_AUTO_START_FILENAME,
        _resolve_state_context_in_worktree,
    )

    parser = argparse.ArgumentParser(
        prog="agdt-retry-autostart",
        description="Retry a failed Copilot autostart using the pending marker file.",
    )
    parser.add_argument(
        "--worktree-path",
        default=None,
        help="Path to the worktree directory (default: current working directory).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip stale-marker check and proceed with retry regardless.",
    )

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    worktree_path: str = args.worktree_path if args.worktree_path else os.getcwd()
    force: bool = args.force

    # --- Read the marker file ------------------------------------------------
    marker_path = os.path.join(worktree_path, ".vscode", _PENDING_AUTO_START_FILENAME)

    if not os.path.isfile(marker_path):
        print(
            f"agdt-retry-autostart: error: no pending auto-start marker found at {marker_path}. No autostart to retry.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        with open(marker_path, encoding="utf-8") as fh:
            marker = json.load(fh)
    except (json.JSONDecodeError, ValueError) as exc:
        print(
            f"agdt-retry-autostart: error: could not parse pending auto-start marker at {marker_path}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
    except OSError as exc:
        print(
            f"agdt-retry-autostart: error: could not read pending auto-start marker at {marker_path}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not isinstance(marker, dict):
        print(
            f"agdt-retry-autostart: error: pending auto-start marker at {marker_path} "
            f"has invalid format (expected JSON object).",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- Validate required fields -------------------------------------------
    for field in ("run_id", "start_prompt"):
        value = marker.get(field)
        if not isinstance(value, str) or not value.strip():
            print(
                f"agdt-retry-autostart: error: pending auto-start marker at "
                f"{marker_path} is missing required field '{field}'.",
                file=sys.stderr,
            )
            sys.exit(1)

    # --- Validate worktree_path from marker ----------------------------------
    marker_wt = marker.get("worktree_path", "")
    effective_wt = args.worktree_path if args.worktree_path else marker_wt
    if not isinstance(effective_wt, str) or not effective_wt or not os.path.isdir(effective_wt):
        print(
            f"agdt-retry-autostart: error: worktree path does not exist or is not a directory: {effective_wt!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    run_id: str = marker["run_id"]

    # --- Stale-marker check (unless --force) ---------------------------------
    state_file_path: Path | None = None
    if not force:
        state_file_path, state_run_id = _resolve_state_context_in_worktree(effective_wt, include_run_id=True)
        if state_file_path is None:
            # State unreadable — warn but proceed (lenient approach per spec).
            print(
                "agdt-retry-autostart: warning: could not read state in worktree; skipping stale-marker check.",
                file=sys.stderr,
            )
        elif state_run_id and state_run_id != run_id:
            print(
                f"agdt-retry-autostart: error: marker run_id ({run_id}) does not "
                f"match current state run_id ({state_run_id}). Use --force to retry "
                f"anyway.",
                file=sys.stderr,
            )
            sys.exit(1)

    # --- Resolve state file for _unmark_run_triggered ------------------------
    if state_file_path is None:
        state_file_path, _ = _resolve_state_context_in_worktree(effective_wt)
    if state_file_path is not None:
        _unmark_run_triggered(state_file_path, run_id)

    # --- Delegate to copilot_auto_start_cmd ----------------------------------
    constructed_argv: list[str] = [
        "--worktree-path",
        effective_wt,
        "--start-prompt",
        marker["start_prompt"],
        "--run-id",
        run_id,
    ]

    model = marker.get("model")
    if isinstance(model, str) and model.strip():
        constructed_argv.extend(["--model", model])

    copilot_auto_start_cmd(argv=constructed_argv)
