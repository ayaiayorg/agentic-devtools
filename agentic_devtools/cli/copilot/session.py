"""
GitHub Copilot CLI session management.

Provides utilities for starting and managing ``gh copilot`` CLI sessions
programmatically, supporting both interactive and non-interactive modes,
with session ID tracking and state persistence.

Research notes
--------------
The ``gh copilot suggest`` command is the primary entry point for the
``gh copilot`` extension.  As of early 2025, autonomous / non-interactive
operation is not natively exposed through a stable flag.  The module
therefore implements non-interactive mode by spawning the process with
stdin/stdout captured to a log file, which is sufficient for pipeline use
cases where no interactive terminal is available.  When a stable
``--non-interactive`` or agent-mode flag is added upstream, the
``_build_copilot_args`` helper can be updated to include it without any
other changes.

Fallback behaviour
------------------
When ``gh copilot`` is not installed or is not callable the session cannot
be started.  The module logs a warning and prints the prompt to stdout so
that the user or pipeline can invoke a session manually.
"""

import shutil
import subprocess
import sys
import uuid
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from agentic_devtools.state import get_state_dir, set_value

from ..subprocess_utils import run_safe

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# State key namespace
_COPILOT_NS = "copilot"

# Log file directory (relative to state dir)
_LOG_DIR_NAME = "background-tasks/logs"

# Prompt file naming pattern
_PROMPT_FILE_PATTERN = "copilot-session-{session_id}-prompt.md"

# Managed install path for the standalone copilot binary
_MANAGED_COPILOT = Path.home() / ".agdt" / "bin" / ("copilot.exe" if sys.platform == "win32" else "copilot")

# Maximum prompt length (in characters) that can safely be passed as a
# positional argument to ``gh copilot suggest``.  Windows' CreateProcess
# imposes a 32,767-character limit on the entire command line; we leave
# headroom for the ``gh copilot suggest`` prefix and OS overhead.
_MAX_GH_COPILOT_ARGV_LENGTH = 30_000


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass
class CopilotSessionResult:
    """Result returned by :func:`start_copilot_session`.

    Attributes:
        session_id: Unique identifier for the session (UUID4 hex).
        mode: ``"interactive"`` or ``"non-interactive"``.
        prompt_file: Absolute path to the temporary prompt file.
        start_time: ISO-8601 UTC timestamp when the session was started.
        pid: Process ID for non-interactive sessions; ``None`` for
            interactive sessions (where the process has already exited
            when this object is returned).
        process: The :class:`subprocess.Popen` handle for non-interactive
            sessions; ``None`` for interactive sessions.
    """

    session_id: str
    mode: str
    prompt_file: str
    start_time: str
    pid: Optional[int] = field(default=None)
    process: Optional[subprocess.Popen] = field(default=None, repr=False)  # type: ignore[type-arg]


# ---------------------------------------------------------------------------
# Availability check
# ---------------------------------------------------------------------------


def _get_copilot_binary() -> Optional[str]:
    """Return the path to the copilot binary, or ``None`` if not found.

    Checks (in order):
    1. The standalone ``copilot`` binary on the system ``PATH``.
    2. The managed install at ``~/.agdt/bin/copilot[.exe]``.

    Returns:
        Absolute path string when found, ``None`` otherwise.
    """
    system_path = shutil.which("copilot")
    if system_path:
        return system_path
    if _MANAGED_COPILOT.is_file():
        return str(_MANAGED_COPILOT)
    return None


def is_gh_copilot_available() -> bool:
    """Return ``True`` if a usable Copilot CLI can be invoked on this machine.

    Checks (in order):
    1. A standalone ``copilot`` binary (system PATH or ``~/.agdt/bin/``).
    2. The ``gh copilot`` extension (legacy fallback): ``gh`` must be present
       and ``gh copilot --help`` must exit with return code 0.

    Returns:
        ``True`` when at least one check passes; ``False`` otherwise.
    """
    # Prefer standalone copilot binary
    if _get_copilot_binary() is not None:
        return True

    # Fallback: gh copilot extension
    if not shutil.which("gh"):
        return False
    try:
        result = run_safe(
            ["gh", "copilot", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _make_session_id() -> str:
    """Generate a new unique session identifier (UUID4 hex string)."""
    return uuid.uuid4().hex


def _get_prompt_file_path(session_id: str) -> Path:
    """Return the path where the prompt file should be written.

    The file is placed inside ``scripts/temp/`` relative to the state
    directory, following the same convention as other temporary files.

    Args:
        session_id: The session identifier.

    Returns:
        Absolute :class:`~pathlib.Path` for the prompt file.
    """
    state_dir = get_state_dir()
    return state_dir / _PROMPT_FILE_PATTERN.format(session_id=session_id)


def _get_log_file_path(session_id: str, start_time: str) -> Path:
    """Return the path for the non-interactive session log file.

    Args:
        session_id: The session identifier.
        start_time: ISO-8601 timestamp (used in the filename).

    Returns:
        Absolute :class:`~pathlib.Path` for the log file.
    """
    state_dir = get_state_dir()
    timestamp = start_time.replace(":", "").replace("-", "").replace(".", "_")[:18]
    filename = f"copilot_session_{timestamp}.log"
    return state_dir / _LOG_DIR_NAME / filename


def _build_copilot_args(prompt: str) -> Optional[list[str]]:
    """Build the copilot argument list.

    Uses the standalone ``copilot`` binary when available (preferred), falling
    back to the ``gh copilot`` extension for backward compatibility.

    Neither the standalone binary nor the ``gh copilot`` extension supports
    ``--file``; the prompt text is passed as the positional ``[subject]``
    argument for both paths.  When the prompt exceeds
    :data:`_MAX_GH_COPILOT_ARGV_LENGTH`, ``None`` is returned so the caller
    can use a fallback.

    Args:
        prompt: The full prompt text to pass as the ``[subject]`` argument.

    Returns:
        List of strings suitable for :func:`subprocess.Popen`, or ``None``
        when the prompt is too large for the argv path.
    """
    if len(prompt) > _MAX_GH_COPILOT_ARGV_LENGTH:
        return None
    standalone = _get_copilot_binary()
    if standalone:
        return [standalone, "suggest", prompt]
    return ["gh", "copilot", "suggest", prompt]


def _persist_session_state(result: CopilotSessionResult) -> None:
    """Write session metadata to ``agdt-state.json``.

    Keys written (all under the ``copilot.`` namespace):
    - ``copilot.session_id``
    - ``copilot.mode``
    - ``copilot.prompt_file``
    - ``copilot.start_time``
    - ``copilot.pid`` (empty string when not applicable)

    Args:
        result: The :class:`CopilotSessionResult` to persist.
    """
    set_value(f"{_COPILOT_NS}.session_id", result.session_id)
    set_value(f"{_COPILOT_NS}.mode", result.mode)
    set_value(f"{_COPILOT_NS}.prompt_file", result.prompt_file)
    set_value(f"{_COPILOT_NS}.start_time", result.start_time)
    set_value(f"{_COPILOT_NS}.pid", result.pid if result.pid is not None else "")


def _print_fallback_prompt(prompt: str) -> None:
    """Print the prompt to stdout as a fallback when ``gh copilot`` is unavailable.

    Args:
        prompt: The full prompt text to display.
    """
    print(
        "WARNING: gh copilot is not available. Please start a session manually with the following prompt:\n",
        file=sys.stderr,
    )
    print(prompt)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def start_copilot_session(
    prompt: str,
    working_directory: str,
    interactive: bool = True,
    session_id: Optional[str] = None,
) -> CopilotSessionResult:
    """Start a ``gh copilot`` CLI session with the given prompt.

    Behaviour:
    - Generates (or reuses) a unique session ID.
    - Writes *prompt* to a temporary file so that large prompts do not
      exceed CLI argument-length limits.
    - Starts ``copilot suggest <prompt>`` (standalone binary) or
      ``gh copilot suggest <prompt>`` (extension fallback).
    - In **interactive** mode the child process inherits the current
      terminal (stdin / stdout / stderr), so the user can interact with
      it directly.  This call blocks until the interactive session ends.
    - In **non-interactive** mode the child process runs in the
      background with stdout and stderr captured to a log file.  The
      call returns immediately.
    - Session metadata is written to ``agdt-state.json`` under the
      ``copilot.*`` namespace.
    - If ``gh copilot`` is not available, a warning is emitted and the
      prompt is printed to stdout so the user can start a session
      manually.

    Args:
        prompt: The full prompt text to send to the Copilot session.
        working_directory: The directory in which to run the command.
            Typically the worktree root.
        interactive: When ``True`` (default) the process runs with an
            attached terminal.  When ``False`` the process runs
            detached in the background.
        session_id: Optional pre-generated session ID.  A new UUID4 hex
            string is generated when this is ``None``.

    Returns:
        A :class:`CopilotSessionResult` with session metadata.

    Raises:
        OSError: If the prompt file cannot be written to disk.
    """
    if session_id is None:
        session_id = _make_session_id()

    start_time = datetime.now(timezone.utc).isoformat()
    mode = "interactive" if interactive else "non-interactive"

    # --- Write prompt to temp file -------------------------------------------
    prompt_file_path = _get_prompt_file_path(session_id)
    prompt_file_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_file_path.write_text(prompt, encoding="utf-8")
    prompt_file = str(prompt_file_path)

    # --- Check availability --------------------------------------------------
    if not is_gh_copilot_available():
        warnings.warn(
            "gh copilot is not available; printing prompt to stdout as fallback.",
            stacklevel=2,
        )
        _print_fallback_prompt(prompt)
        result = CopilotSessionResult(
            session_id=session_id,
            mode=mode,
            prompt_file=prompt_file,
            start_time=start_time,
            pid=None,
            process=None,
        )
        _persist_session_state(result)
        return result

    # --- Build command -------------------------------------------------------
    args = _build_copilot_args(prompt)

    # When the prompt is too large for the gh copilot argv path (no
    # standalone binary available), fall back to printing the prompt.
    if args is None:
        warnings.warn(
            "Prompt too large for gh copilot argv; printing prompt to stdout as fallback.",
            stacklevel=2,
        )
        _print_fallback_prompt(prompt)
        result = CopilotSessionResult(
            session_id=session_id,
            mode=mode,
            prompt_file=prompt_file,
            start_time=start_time,
            pid=None,
            process=None,
        )
        _persist_session_state(result)
        return result

    # --- Launch process -------------------------------------------------------
    if interactive:
        # Inherit stdio so the user can interact with the session.
        # This call blocks until the interactive session ends.
        # shell=False is required: gh is a proper .exe (not a .cmd batch script),
        # and the argument list contains a file path derived from user-supplied
        # prompt content; shell=True on Windows would allow cmd.exe to expand
        # %VAR% patterns inside those values.
        process = subprocess.Popen(
            args,
            cwd=working_directory,
            shell=False,
        )
        process.wait()
        result = CopilotSessionResult(
            session_id=session_id,
            mode=mode,
            prompt_file=prompt_file,
            start_time=start_time,
            pid=None,  # process has already exited; PID not meaningful
            process=None,
        )
    else:
        # Non-interactive: run as background process, capture output to log file.
        log_file_path = _get_log_file_path(session_id, start_time)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Open without a context manager so the file handle stays open while the
        # background process is still running; the OS will release it when the
        # child process (which inherits the fd) eventually exits.
        # shell=False: same reasoning as the interactive case above.
        log_fh = open(log_file_path, "w", encoding="utf-8")  # noqa: WPS515
        process = subprocess.Popen(
            args,
            cwd=working_directory,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True if sys.platform != "win32" else False,
            shell=False,
        )

        result = CopilotSessionResult(
            session_id=session_id,
            mode=mode,
            prompt_file=prompt_file,
            start_time=start_time,
            pid=process.pid,
            process=process,
        )

    _persist_session_state(result)
    return result
