"""
Core utilities for git CLI commands.

This module provides low-level helpers used by git operations:
- State management helpers
- Git command execution
- Temporary file handling
"""

import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from subprocess import CompletedProcess
from typing import Generator

from ...state import get_value
from ..subprocess_utils import run_safe

# State keys
STATE_COMMIT_MESSAGE = "commit_message"
STATE_DRY_RUN = "dry_run"
STATE_SKIP_STAGE = "skip_stage"
STATE_SKIP_PUBLISH = "skip_publish"
STATE_SKIP_PUSH = "skip_push"
STATE_SKIP_REBASE = "skip_rebase"

# Boolean truthy values for state parsing
_TRUTHY_VALUES = (True, "true", "1", "yes")


def get_bool_state(key: str, default: bool = False) -> bool:
    """
    Get a boolean value from state.

    Args:
        key: The state key to read
        default: Default value if key not found

    Returns:
        Boolean value
    """
    value = get_value(key)
    if value is None:
        return default
    return value in _TRUTHY_VALUES


def run_git(*args: str, check: bool = True) -> CompletedProcess:
    """
    Run a git command and return the result.

    Uses run_safe for keyboard interrupt protection and proper encoding.

    Args:
        *args: Git command arguments (e.g., 'add', '.')
        check: If True, raise on non-zero exit code

    Returns:
        CompletedProcess result

    Raises:
        SystemExit: If check=True and git command fails
    """
    cmd = ["git"] + list(args)
    result = run_safe(
        cmd,
        capture_output=True,
        text=True,
    )

    if check and result.returncode != 0:
        error_msg = f"Error: git {' '.join(args)} failed"
        print(error_msg, file=sys.stderr)
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        sys.exit(result.returncode)

    return result


def get_current_branch() -> str:
    """
    Get the current git branch name.

    Returns:
        The current branch name

    Raises:
        SystemExit: If not on a branch (detached HEAD) or unable to determine
    """
    result = run_git("rev-parse", "--abbrev-ref", "HEAD")
    branch = result.stdout.strip()

    if not branch or branch == "HEAD":
        print(
            "Error: Unable to determine current branch name (detached HEAD?)",
            file=sys.stderr,
        )
        sys.exit(1)

    return branch


def get_commit_message() -> str:
    """
    Get the commit message from state.

    The message is retrieved from the 'commit_message' key in state.
    Multiline messages are supported natively!

    Returns:
        The commit message string

    Raises:
        SystemExit: If no commit message is set in state
    """
    message = get_value(STATE_COMMIT_MESSAGE)

    if not message:
        print(
            f'Error: No commit message set. Use: dfly-set {STATE_COMMIT_MESSAGE} "Your message"',
            file=sys.stderr,
        )
        sys.exit(1)

    return str(message)


@contextmanager
def temp_message_file(message: str) -> Generator[str, None, None]:
    """
    Create a temporary file with the commit message.

    This context manager ensures the temp file is cleaned up properly.

    Args:
        message: The commit message to write

    Yields:
        Path to the temporary file
    """
    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
    try:
        temp_file.write(message)
        temp_file.close()  # Close before git reads it (Windows compatibility)
        yield temp_file.name
    finally:
        try:
            Path(temp_file.name).unlink(missing_ok=True)
        except OSError:
            pass  # Best effort cleanup
