"""
Subprocess utilities for safe command execution.

These utilities ensure subprocess calls complete even when external signals
(like terminal interrupts from VS Code tool calls) occur.
"""

import signal
import subprocess
import sys
from typing import Any, Dict, List, Optional, Union


def run_safe(
    args: Union[str, List[str]],
    *,
    capture_output: bool = False,
    text: bool = False,
    check: bool = False,
    shell: Optional[bool] = None,
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
    timeout: Optional[float] = None,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """
    Run a subprocess with signal handling to prevent interruption.

    This wrapper temporarily ignores SIGINT (Ctrl+C) during subprocess execution
    to ensure commands complete even when external tools send interrupt signals.

    On Windows, shell=True is automatically enabled when args is a list to handle
    commands like 'az' which are batch scripts (az.cmd) that can't be found without shell.

    Args:
        args: Command and arguments to run.
        capture_output: Capture stdout and stderr.
        text: Return stdout/stderr as strings.
        check: Raise CalledProcessError on non-zero exit.
        shell: Run command through shell. On Windows, defaults to True for list args.
        env: Environment variables for the subprocess.
        cwd: Working directory for the subprocess.
        timeout: Timeout in seconds.
        encoding: Text encoding for stdout/stderr (default: utf-8 when text=True).
        errors: Error handling for encoding (default: replace).
        **kwargs: Additional arguments passed to subprocess.run.

    Returns:
        CompletedProcess instance with return code and output.
    """
    # Validate args - empty command list is not allowed
    if isinstance(args, list) and len(args) == 0:
        raise ValueError("Empty command list is not allowed")

    # Store original signal handler
    original_handler = None
    if sys.platform != "win32":
        # On Unix, temporarily ignore SIGINT
        original_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)

    # On Windows, default to shell=True for list args to handle .cmd/.bat scripts
    # Commands like 'az', 'npm', etc. are batch scripts on Windows
    if shell is None:
        shell = sys.platform == "win32" and isinstance(args, list)

    # Use UTF-8 encoding with error replacement by default on Windows
    # to avoid UnicodeDecodeError with cp1252
    if text and encoding is None:
        encoding = "utf-8"
    if text and errors is None:
        errors = "replace"

    try:
        return subprocess.run(  # nosec B602 - shell=True only enabled on Windows for .cmd/.bat scripts; args is always a list
            args,
            capture_output=capture_output,
            text=text,
            check=check,
            shell=shell,
            env=env,
            cwd=cwd,
            timeout=timeout,
            encoding=encoding,
            errors=errors,
            **kwargs,
        )
    except KeyboardInterrupt:
        # If somehow an interrupt gets through, return a failed result
        # instead of crashing
        return subprocess.CompletedProcess(
            args=args if isinstance(args, str) else args,
            returncode=-1,
            stdout="" if text else b"",
            stderr="Interrupted" if text else b"Interrupted",
        )
    except UnicodeDecodeError:
        # Handle encoding errors by returning empty result
        return subprocess.CompletedProcess(
            args=args if isinstance(args, str) else args,
            returncode=-2,
            stdout="" if text else b"",
            stderr="Encoding error" if text else b"Encoding error",
        )
    finally:
        # Restore original signal handler
        if original_handler is not None:
            signal.signal(signal.SIGINT, original_handler)
