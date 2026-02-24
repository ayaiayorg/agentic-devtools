"""
Background task execution infrastructure.

Provides functionality to run CLI commands in detached background processes
with output logging and status tracking.
"""

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .task_state import (
    BackgroundTask,
    TaskStatus,
    add_task,
    get_logs_dir,
    get_task_by_id,
)

# Log file format
LOG_FILE_FORMAT = "{command}_{timestamp}.log"


def create_log_file_path(command: str) -> Path:
    """
    Create a unique log file path for a command.

    Args:
        command: The command name (e.g., "agdt-git-save-work")

    Returns:
        Path to the new log file
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    # Sanitize command name for filename
    safe_command = command.replace("-", "_").replace(" ", "_")
    filename = LOG_FILE_FORMAT.format(command=safe_command, timestamp=timestamp)
    return get_logs_dir() / filename


def _get_python_executable() -> str:
    """Get the current Python executable path."""
    return sys.executable


def _build_runner_script(
    command: str,
    task_id: str,
    log_file: Path,
    cwd: Optional[str] = None,
) -> str:
    """
    Build a Python script that runs the command and updates task state.

    This script is executed in the background subprocess and handles:
    - Redirecting output to log file
    - Updating task status in state
    - Capturing exit codes

    Args:
        command: The CLI command to run
        task_id: The task ID for state updates
        log_file: Path to write logs to
        cwd: Working directory for the command

    Returns:
        Python script as a string
    """
    # Get the path to this package for imports
    package_dir = Path(__file__).parent.parent

    script = f"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add package to path for imports
sys.path.insert(0, {repr(str(package_dir))})

from agentic_devtools.task_state import (
    get_task_by_id,
    update_task,
    TaskStatus,
)

def main():
    task_id = {repr(task_id)}
    log_file = Path({repr(str(log_file))})
    command = {repr(command)}
    cwd = {repr(cwd)}

    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Open log file for writing
    with open(log_file, "w", encoding="utf-8") as log:
        # Write header
        start_time = datetime.now(timezone.utc).isoformat()
        log.write(f"=== Task {{task_id}} ===\\n")
        log.write(f"Command: {{command}}\\n")
        log.write(f"Started: {{start_time}}\\n")
        log.write(f"Working Directory: {{cwd or os.getcwd()}}\\n")
        log.write("=" * 50 + "\\n\\n")
        log.flush()

        # Update task to running status
        task = get_task_by_id(task_id)
        if task:
            task.mark_running()
            update_task(task)

        # Run the command with UTF-8 encoding for child process stdout
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            result = subprocess.run(
                command,
                shell=True,
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            exit_code = result.returncode
            error_message = None
        except Exception as e:
            exit_code = 1
            error_message = str(e)
            log.write(f"\\n\\n!!! Exception: {{error_message}}\\n")

        # Write footer
        end_time = datetime.now(timezone.utc).isoformat()
        log.write("\\n" + "=" * 50 + "\\n")
        log.write(f"Completed: {{end_time}}\\n")
        log.write(f"Exit Code: {{exit_code}}\\n")
        log.flush()

        # Update task to completed/failed status
        task = get_task_by_id(task_id)
        if task:
            if exit_code == 0:
                task.mark_completed(exit_code)
            else:
                task.mark_failed(exit_code, error_message)
            update_task(task)

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
"""
    return script


def run_in_background(
    command: str,
    args: Optional[Dict[str, Any]] = None,
    cwd: Optional[str] = None,
) -> BackgroundTask:
    """
    Run a CLI command in a detached background process.

    The command runs in a separate process that:
    - Continues running even if the parent process exits
    - Writes all output to a log file
    - Updates task state with progress and completion

    Args:
        command: The CLI command to run (e.g., "agdt-git-save-work")
        args: Additional arguments/context to store with the task
        cwd: Working directory for the command

    Returns:
        BackgroundTask object representing the spawned task
    """
    # Create log file path
    log_file = create_log_file_path(command)

    # Create task record
    task = BackgroundTask.create(
        command=command,
        log_file=log_file,
        args=args,
    )

    # Add task to state
    add_task(task)

    # Build runner script
    runner_script = _build_runner_script(
        command=command,
        task_id=task.id,
        log_file=log_file,
        cwd=cwd,
    )

    # Get Python executable
    python_exe = _get_python_executable()

    # Set up environment with UTF-8 encoding for child process
    import os as _os

    env = _os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    # Launch detached process
    if sys.platform == "win32":
        # Windows: Use CREATE_NO_WINDOW to prevent console windows from opening
        # Combined with CREATE_NEW_PROCESS_GROUP for proper signal handling
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        subprocess.Popen(
            [python_exe, "-c", runner_script],
            creationflags=creation_flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
            cwd=cwd,
            env=env,
        )
    else:
        # Unix: Use double-fork or nohup-like behavior
        subprocess.Popen(
            [python_exe, "-c", runner_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
            cwd=cwd,
            env=env,
        )

    return task


def _build_function_runner_script(
    module_path: str,
    function_name: str,
    task_id: str,
    log_file: Path,
    cwd: Optional[str] = None,
) -> str:
    """
    Build a Python script that imports and runs a function, updating task state.

    Args:
        module_path: Full module path (e.g., "agentic_devtools.cli.jira.comment_commands")
        function_name: Name of the function to call (e.g., "add_comment")
        task_id: The task ID for state updates
        log_file: Path to write logs to
        cwd: Working directory for the function

    Returns:
        Python script as a string
    """
    package_dir = Path(__file__).parent.parent

    script = f"""
import io
import os
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from pathlib import Path

# Add package to path for imports
sys.path.insert(0, {repr(str(package_dir))})

from agentic_devtools.task_state import (
    get_task_by_id,
    update_task,
    TaskStatus,
)

def main():
    task_id = {repr(task_id)}
    log_file = Path({repr(str(log_file))})
    module_path = {repr(module_path)}
    function_name = {repr(function_name)}
    cwd = {repr(cwd)}

    # Change to working directory if specified
    if cwd:
        os.chdir(cwd)

    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Open log file for writing
    with open(log_file, "w", encoding="utf-8") as log:
        # Write header
        start_time = datetime.now(timezone.utc).isoformat()
        log.write(f"=== Task {{task_id}} ===\\n")
        log.write(f"Function: {{module_path}}.{{function_name}}\\n")
        log.write(f"Started: {{start_time}}\\n")
        log.write(f"Working Directory: {{os.getcwd()}}\\n")
        log.write("=" * 50 + "\\n\\n")
        log.flush()

        # Update task to running status
        task = get_task_by_id(task_id)
        if task:
            task.mark_running()
            update_task(task)

        # Capture stdout/stderr to log
        exit_code = 0
        error_message = None

        try:
            # Import the module and get the function
            import importlib
            module = importlib.import_module(module_path)
            func = getattr(module, function_name)

            # Redirect stdout/stderr to log file
            # Create a writer that writes to both the log and flushes
            class LogWriter:
                def __init__(self, log_file):
                    self.log = log_file
                def write(self, text):
                    self.log.write(text)
                    self.log.flush()
                def flush(self):
                    self.log.flush()

            log_writer = LogWriter(log)

            with redirect_stdout(log_writer), redirect_stderr(log_writer):
                # Call the function
                result = func()
                # If function returns an int, use as exit code
                if isinstance(result, int):
                    exit_code = result

        except SystemExit as e:
            # Function called sys.exit()
            exit_code = e.code if isinstance(e.code, int) else (1 if e.code else 0)
        except Exception as e:
            exit_code = 1
            error_message = str(e)
            log.write(f"\\n\\n!!! Exception: {{error_message}}\\n")
            log.write(traceback.format_exc())

        # Write footer
        end_time = datetime.now(timezone.utc).isoformat()
        log.write("\\n" + "=" * 50 + "\\n")
        log.write(f"Completed: {{end_time}}\\n")
        log.write(f"Exit Code: {{exit_code}}\\n")
        log.flush()

        # Update task to completed/failed status
        task = get_task_by_id(task_id)
        if task:
            if exit_code == 0:
                task.mark_completed(exit_code)
            else:
                task.mark_failed(exit_code, error_message)
            update_task(task)

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
"""
    return script


def run_function_in_background(
    module_path: str,
    function_name: str,
    command_display_name: Optional[str] = None,
    args: Optional[Dict[str, Any]] = None,
    cwd: Optional[str] = None,
) -> BackgroundTask:
    """
    Run a Python function in a detached background process.

    The function is imported and called directly, with stdout/stderr
    captured to a log file.

    Args:
        module_path: Full module path (e.g., "agentic_devtools.cli.jira.comment_commands")
        function_name: Name of the function to call (e.g., "add_comment")
        command_display_name: Human-readable name for the task (defaults to function_name)
        args: Additional arguments/context to store with the task
        cwd: Working directory for the function

    Returns:
        BackgroundTask object representing the spawned task

    Example:
        task = run_function_in_background(
            "agentic_devtools.cli.jira.comment_commands",
            "add_comment",
            command_display_name="agdt-add-jira-comment"
        )
    """
    display_name = command_display_name or function_name

    # Create log file path
    log_file = create_log_file_path(display_name)

    # Create task record
    task = BackgroundTask.create(
        command=display_name,
        log_file=log_file,
        args=args,
    )

    # Add task to state
    add_task(task)

    # Build runner script
    runner_script = _build_function_runner_script(
        module_path=module_path,
        function_name=function_name,
        task_id=task.id,
        log_file=log_file,
        cwd=cwd,
    )

    # Get Python executable
    python_exe = _get_python_executable()

    # Set up environment with UTF-8 encoding for child process
    import os as _os

    env = _os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    # Launch detached process
    if sys.platform == "win32":
        # Windows: Use CREATE_NO_WINDOW to prevent console windows from opening
        # Combined with CREATE_NEW_PROCESS_GROUP for proper signal handling
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        subprocess.Popen(
            [python_exe, "-c", runner_script],
            creationflags=creation_flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
            cwd=cwd,
            env=env,
        )
    else:
        subprocess.Popen(
            [python_exe, "-c", runner_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
            cwd=cwd,
            env=env,
        )

    return task


def wait_for_task(
    task_id: str,
    poll_interval: float = 0.5,
    timeout: Optional[float] = None,
) -> Tuple[bool, Optional[int]]:
    """
    Wait for a background task to complete.

    Args:
        task_id: ID of the task to wait for
        poll_interval: Seconds between status checks
        timeout: Maximum seconds to wait (None for infinite)

    Returns:
        Tuple of (success, exit_code):
        - success: True if task completed successfully
        - exit_code: The task's exit code (None if timeout or not found)
    """
    import time

    start_time = time.time()

    while True:
        task = get_task_by_id(task_id)

        if task is None:
            return (False, None)

        if task.is_terminal():
            return (task.status == TaskStatus.COMPLETED, task.exit_code)

        if timeout is not None and (time.time() - start_time) > timeout:
            return (False, None)

        time.sleep(poll_interval)


def get_task_log_content(task_id: str, tail_lines: Optional[int] = None) -> Optional[str]:
    """
    Get the content of a task's log file.

    Args:
        task_id: ID of the task
        tail_lines: If specified, only return the last N lines

    Returns:
        Log file content as string, or None if task/log not found
    """
    task = get_task_by_id(task_id)

    if task is None or task.log_file is None:
        return None

    log_path = Path(task.log_file)

    if not log_path.exists():
        return None  # pragma: no cover

    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")

        if tail_lines is not None:  # pragma: no cover
            lines = content.splitlines()
            content = "\n".join(lines[-tail_lines:])

        return content
    except OSError:  # pragma: no cover
        return None


def cleanup_old_logs(max_age_hours: float = 24, max_count: Optional[int] = None) -> int:
    """
    Clean up old log files.

    Args:
        max_age_hours: Delete logs older than this many hours
        max_count: Keep at most this many log files (oldest deleted first)

    Returns:
        Number of log files deleted
    """
    from datetime import timedelta

    logs_dir = get_logs_dir()
    deleted_count = 0

    if not logs_dir.exists():
        return 0  # pragma: no cover

    # Get all log files with their modification times
    log_files: List[Tuple[Path, float]] = []
    for log_file in logs_dir.glob("*.log"):
        try:
            mtime = log_file.stat().st_mtime
            log_files.append((log_file, mtime))
        except OSError:
            continue

    # Sort by modification time (oldest first)
    log_files.sort(key=lambda x: x[1])

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    cutoff_timestamp = cutoff_time.timestamp()

    # Delete old files
    for log_file, mtime in log_files:
        if mtime < cutoff_timestamp:
            try:
                log_file.unlink()
                deleted_count += 1
            except OSError:
                pass

    # Delete excess files if max_count specified
    if max_count is not None:
        remaining = [f for f in logs_dir.glob("*.log")]
        remaining.sort(key=lambda x: x.stat().st_mtime)

        while len(remaining) > max_count:
            oldest = remaining.pop(0)
            try:
                oldest.unlink()
                deleted_count += 1
            except OSError:
                pass

    return deleted_count
