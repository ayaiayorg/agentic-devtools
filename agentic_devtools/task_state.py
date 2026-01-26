"""
Background task state management.

Manages the state of background tasks including:
- Task creation with unique IDs
- Status tracking (pending, running, completed, failed)
- Recent tasks in main state (unfinished or finished within 5 minutes)
- Complete task history in all-background-tasks.json
- Task expiration and cleanup
- Query and filtering operations

Storage structure:
- Main state (dfly-state.json): background.recentTasks (unfinished or recent)
- History file (background-tasks/all-background-tasks.json): complete task history
- Logs: background-tasks/logs/*.log
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .state import get_state_dir, load_state, save_state

# Default task retention period for cleanup (24 hours)
DEFAULT_RETENTION_HOURS = 24

# Time to keep finished tasks in recent list (5 minutes)
RECENT_TASKS_RETENTION_MINUTES = 5

# Directory names
BACKGROUND_TASKS_DIR_NAME = "background-tasks"
LOGS_DIR_NAME = "logs"
ALL_TASKS_FILENAME = "all-background-tasks.json"

# State key paths
BACKGROUND_KEY = "background"
RECENT_TASKS_KEY = "recentTasks"


class TaskStatus(str, Enum):
    """Status values for background tasks."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def _sort_tasks(tasks: List["BackgroundTask"]) -> List["BackgroundTask"]:
    """
    Sort tasks with custom ordering:
    - Unfinished tasks first (no end_time), sorted by start_time (earliest first)
    - Finished tasks second, sorted by end_time (earliest first)

    Args:
        tasks: List of tasks to sort

    Returns:
        Sorted list of tasks
    """

    def sort_key(task: "BackgroundTask") -> tuple:
        # Parse times for comparison
        try:
            start_dt = datetime.fromisoformat(task.start_time.replace("Z", "+00:00"))
        except (ValueError, TypeError, AttributeError):
            start_dt = datetime.min.replace(tzinfo=timezone.utc)

        if task.end_time:
            try:
                end_dt = datetime.fromisoformat(task.end_time.replace("Z", "+00:00"))
            except (ValueError, TypeError, AttributeError):
                end_dt = datetime.max.replace(tzinfo=timezone.utc)
            # Finished tasks: sort group 1, by end_time
            return (1, end_dt, start_dt)
        else:
            # Unfinished tasks: sort group 0, by start_time
            return (0, datetime.max.replace(tzinfo=timezone.utc), start_dt)

    return sorted(tasks, key=sort_key)


@dataclass
class BackgroundTask:
    """
    Represents a background task.

    Attributes:
        id: Unique identifier for the task (UUID)
        command: The CLI command that was executed
        status: Current task status
        start_time: ISO timestamp when task started
        end_time: ISO timestamp when task completed (None if still running)
        log_file: Path to the task's log file
        exit_code: Process exit code (None if not completed)
        args: Additional arguments passed to the command
        error_message: Error message if task failed
    """

    id: str
    command: str
    status: TaskStatus
    start_time: str
    end_time: Optional[str] = None
    log_file: Optional[str] = None
    exit_code: Optional[int] = None
    args: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    @classmethod
    def create(
        cls,
        command: str,
        log_file: Optional[Path] = None,
        args: Optional[Dict[str, Any]] = None,
    ) -> "BackgroundTask":
        """
        Create a new background task with pending status.

        Args:
            command: The CLI command being executed
            log_file: Path to the log file for this task
            args: Additional arguments for the command

        Returns:
            New BackgroundTask instance
        """
        return cls(
            id=str(uuid.uuid4()),
            command=command,
            status=TaskStatus.PENDING,
            start_time=datetime.now(timezone.utc).isoformat(),
            log_file=str(log_file) if log_file else None,
            args=args or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "command": self.command,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "logFile": self.log_file,
            "exitCode": self.exit_code,
            "args": self.args,
            "errorMessage": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BackgroundTask":
        """Create a BackgroundTask from a dictionary."""
        status_value = data.get("status", TaskStatus.PENDING.value)
        if isinstance(status_value, str):
            try:
                status = TaskStatus(status_value)
            except ValueError:
                status = TaskStatus.PENDING
        else:
            status = status_value

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            command=data.get("command", "unknown"),
            status=status,
            start_time=data.get("startTime", datetime.now(timezone.utc).isoformat()),
            end_time=data.get("endTime"),
            log_file=data.get("logFile"),
            exit_code=data.get("exitCode"),
            args=data.get("args", {}),
            error_message=data.get("errorMessage"),
        )

    def mark_running(self) -> None:
        """Mark task as running."""
        self.status = TaskStatus.RUNNING

    def mark_completed(self, exit_code: int = 0) -> None:
        """Mark task as completed with exit code."""
        self.status = TaskStatus.COMPLETED
        self.exit_code = exit_code
        self.end_time = datetime.now(timezone.utc).isoformat()

    def mark_failed(self, exit_code: int = 1, error_message: Optional[str] = None) -> None:
        """Mark task as failed with exit code and optional error message."""
        self.status = TaskStatus.FAILED
        self.exit_code = exit_code
        self.end_time = datetime.now(timezone.utc).isoformat()
        self.error_message = error_message

    def is_terminal(self) -> bool:
        """Check if task is in a terminal state (completed or failed)."""
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)

    def is_expired(self, retention_hours: float = DEFAULT_RETENTION_HOURS) -> bool:
        """
        Check if task has expired based on retention period.

        Args:
            retention_hours: Hours to retain completed tasks

        Returns:
            True if task is completed and older than retention period
        """
        if not self.is_terminal() or not self.end_time:
            return False

        try:
            end_dt = datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))
            expiry_time = end_dt + timedelta(hours=retention_hours)
            return datetime.now(timezone.utc) > expiry_time
        except (ValueError, TypeError):
            return False

    def is_recent(self, retention_minutes: float = RECENT_TASKS_RETENTION_MINUTES) -> bool:
        """
        Check if task should be kept in recent tasks list.

        A task is recent if:
        - It is not finished (no end_time), OR
        - It finished within the retention period

        Args:
            retention_minutes: Minutes to keep finished tasks in recent list

        Returns:
            True if task should be in recent tasks
        """
        if not self.end_time:
            return True  # Unfinished tasks are always recent

        try:
            end_dt = datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=retention_minutes)
            return end_dt > cutoff_time
        except (ValueError, TypeError):
            return True  # If we can't parse, keep it

    def duration_seconds(self) -> Optional[float]:
        """Get task duration in seconds, or None if not completed."""
        if not self.end_time:
            # For running tasks, calculate current duration
            if self.status == TaskStatus.RUNNING:
                try:
                    start_dt = datetime.fromisoformat(self.start_time.replace("Z", "+00:00"))
                    return (datetime.now(timezone.utc) - start_dt).total_seconds()
                except (ValueError, TypeError):
                    return None
            return None

        try:
            start_dt = datetime.fromisoformat(self.start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))
            return (end_dt - start_dt).total_seconds()
        except (ValueError, TypeError):
            return None


# =============================================================================
# Directory and File Path Functions
# =============================================================================


def get_background_tasks_dir() -> Path:
    """
    Get the directory for background tasks storage.

    Returns:
        Path to scripts/temp/background-tasks/
    """
    tasks_dir = get_state_dir() / BACKGROUND_TASKS_DIR_NAME
    tasks_dir.mkdir(parents=True, exist_ok=True)
    return tasks_dir


def get_logs_dir() -> Path:
    """
    Get the directory for task log files.

    Returns:
        Path to scripts/temp/background-tasks/logs/
    """
    logs_dir = get_background_tasks_dir() / LOGS_DIR_NAME
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_all_tasks_file_path() -> Path:
    """
    Get the path to the all-background-tasks.json file.

    Returns:
        Path to scripts/temp/background-tasks/all-background-tasks.json
    """
    return get_background_tasks_dir() / ALL_TASKS_FILENAME


# =============================================================================
# Recent Tasks Functions (stored in main state file)
# =============================================================================


def _get_recent_tasks_from_state(state: Dict[str, Any]) -> List[BackgroundTask]:
    """
    Extract recent tasks from state dictionary.

    Args:
        state: The loaded state dictionary

    Returns:
        List of BackgroundTask objects from background.recentTasks
    """
    background = state.get(BACKGROUND_KEY, {})
    if not isinstance(background, dict):
        return []

    tasks_data = background.get(RECENT_TASKS_KEY, [])
    if not isinstance(tasks_data, list):
        return []

    return [BackgroundTask.from_dict(task) for task in tasks_data]


def _save_recent_tasks_to_state(state: Dict[str, Any], tasks: List[BackgroundTask]) -> Dict[str, Any]:
    """
    Save recent tasks to state dictionary (in-place modification).

    Args:
        state: The state dictionary to modify
        tasks: List of tasks to save

    Returns:
        The modified state dictionary
    """
    if BACKGROUND_KEY not in state:
        state[BACKGROUND_KEY] = {}
    elif not isinstance(state[BACKGROUND_KEY], dict):
        state[BACKGROUND_KEY] = {}

    # Sort and save
    sorted_tasks = _sort_tasks(tasks)
    state[BACKGROUND_KEY][RECENT_TASKS_KEY] = [task.to_dict() for task in sorted_tasks]
    return state


def get_recent_tasks(use_locking: bool = True) -> List[BackgroundTask]:
    """
    Get recent background tasks from state.

    Args:
        use_locking: Whether to use file locking for thread safety

    Returns:
        List of BackgroundTask objects (sorted)
    """
    state = load_state(use_locking=use_locking)
    tasks = _get_recent_tasks_from_state(state)
    return _sort_tasks(tasks)


def _prune_and_archive_old_tasks(tasks: List[BackgroundTask], use_locking: bool = True) -> List[BackgroundTask]:
    """
    Separate tasks into recent and old, archive old ones.

    Args:
        tasks: All tasks to process
        use_locking: Whether to use file locking

    Returns:
        List of recent tasks only
    """
    recent_tasks = []
    old_tasks = []

    for task in tasks:
        if task.is_recent():
            recent_tasks.append(task)
        else:
            old_tasks.append(task)

    # Archive old tasks to all-background-tasks.json
    if old_tasks:
        _append_to_all_tasks(old_tasks, use_locking=use_locking)

    return recent_tasks


# =============================================================================
# All Tasks Functions (stored in separate JSON file)
# =============================================================================


def _load_all_tasks_file() -> List[Dict[str, Any]]:
    """
    Load all tasks from the all-background-tasks.json file.

    Returns:
        List of task dictionaries
    """
    file_path = get_all_tasks_file_path()
    if not file_path.exists():
        return []

    try:
        content = file_path.read_text(encoding="utf-8")
        data = json.loads(content) if content.strip() else []
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_all_tasks_file(tasks_data: List[Dict[str, Any]]) -> None:
    """
    Save tasks to the all-background-tasks.json file.

    Args:
        tasks_data: List of task dictionaries to save
    """
    file_path = get_all_tasks_file_path()
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Sort before saving
    tasks = [BackgroundTask.from_dict(t) for t in tasks_data]
    sorted_tasks = _sort_tasks(tasks)

    content = json.dumps([t.to_dict() for t in sorted_tasks], indent=2, ensure_ascii=False)
    file_path.write_text(content, encoding="utf-8")


def _append_to_all_tasks(tasks: List[BackgroundTask], use_locking: bool = True) -> None:
    """
    Append tasks to the all-background-tasks.json file.

    Args:
        tasks: Tasks to append
        use_locking: Whether to use file locking (for future use)
    """
    existing_data = _load_all_tasks_file()
    existing_ids = {t.get("id") for t in existing_data}

    # Add new tasks that aren't already in the file
    for task in tasks:
        if task.id not in existing_ids:
            existing_data.append(task.to_dict())
            existing_ids.add(task.id)

    _save_all_tasks_file(existing_data)


def get_all_tasks() -> List[BackgroundTask]:
    """
    Get all tasks from the all-background-tasks.json file.

    Returns:
        List of all BackgroundTask objects (sorted)
    """
    tasks_data = _load_all_tasks_file()
    tasks = [BackgroundTask.from_dict(t) for t in tasks_data]
    return _sort_tasks(tasks)


def get_task_from_all_tasks(task_id: str) -> Optional[BackgroundTask]:
    """
    Look up a task by ID in the all-background-tasks.json file.

    Args:
        task_id: The task ID to look up

    Returns:
        BackgroundTask if found, None otherwise
    """
    tasks = get_all_tasks()

    for task in tasks:
        if task.id == task_id:
            return task

    # Also try partial ID match (first 8 characters)
    if len(task_id) >= 8:
        for task in tasks:
            if task.id.startswith(task_id):
                return task

    return None


# =============================================================================
# Main Task Management Functions (public API)
# =============================================================================


def get_background_tasks(use_locking: bool = True) -> List[BackgroundTask]:
    """
    Get all background tasks from recent list (for backward compatibility).

    This returns only recent tasks. Use get_all_tasks() for complete history.

    Args:
        use_locking: Whether to use file locking for thread safety

    Returns:
        List of recent BackgroundTask objects (sorted)
    """
    return get_recent_tasks(use_locking=use_locking)


def save_background_tasks(tasks: List[BackgroundTask], use_locking: bool = True) -> None:
    """
    Save background tasks to state (prunes old tasks automatically).

    Args:
        tasks: List of BackgroundTask objects to save
        use_locking: Whether to use file locking for thread safety
    """
    state = load_state(use_locking=use_locking)

    # Prune old tasks and archive them
    recent_tasks = _prune_and_archive_old_tasks(tasks, use_locking=use_locking)

    # Save recent tasks to state
    _save_recent_tasks_to_state(state, recent_tasks)
    save_state(state, use_locking=use_locking)


def add_task(task: BackgroundTask, use_locking: bool = True) -> None:
    """
    Add a new task to the background tasks list.

    Args:
        task: BackgroundTask to add
        use_locking: Whether to use file locking for thread safety
    """
    state = load_state(use_locking=use_locking)
    tasks = _get_recent_tasks_from_state(state)
    tasks.append(task)

    # Also add to all-tasks file immediately
    _append_to_all_tasks([task], use_locking=use_locking)

    # Prune and save recent tasks
    recent_tasks = _prune_and_archive_old_tasks(tasks, use_locking=use_locking)
    _save_recent_tasks_to_state(state, recent_tasks)
    save_state(state, use_locking=use_locking)


def update_task(task: BackgroundTask, use_locking: bool = True) -> bool:
    """
    Update an existing task in the background tasks list.

    Args:
        task: BackgroundTask with updated values
        use_locking: Whether to use file locking for thread safety

    Returns:
        True if task was found and updated, False otherwise
    """
    state = load_state(use_locking=use_locking)
    tasks = _get_recent_tasks_from_state(state)

    found = False
    for i, existing in enumerate(tasks):
        if existing.id == task.id:
            tasks[i] = task
            found = True
            break

    if found:
        # Update in all-tasks file as well
        _update_task_in_all_tasks(task)

        # Prune and save recent tasks
        recent_tasks = _prune_and_archive_old_tasks(tasks, use_locking=use_locking)
        _save_recent_tasks_to_state(state, recent_tasks)
        save_state(state, use_locking=use_locking)
        return True

    return False


def _update_task_in_all_tasks(task: BackgroundTask) -> None:
    """
    Update a task in the all-background-tasks.json file.

    Args:
        task: Task with updated values
    """
    tasks_data = _load_all_tasks_file()

    for i, t in enumerate(tasks_data):
        if t.get("id") == task.id:
            tasks_data[i] = task.to_dict()
            break
    else:
        # Task not found, append it
        tasks_data.append(task.to_dict())

    _save_all_tasks_file(tasks_data)


def get_task_by_id(task_id: str, use_locking: bool = True) -> Optional[BackgroundTask]:
    """
    Get a specific task by ID.

    First checks recent tasks, then falls back to all-tasks file.

    Args:
        task_id: The task ID to look up
        use_locking: Whether to use file locking for thread safety

    Returns:
        BackgroundTask if found, None otherwise
    """
    # First check recent tasks
    tasks = get_recent_tasks(use_locking=use_locking)

    for task in tasks:
        if task.id == task_id:
            return task

    # Also try partial ID match (first 8 characters)
    if len(task_id) >= 8:
        for task in tasks:
            if task.id.startswith(task_id):
                return task

    # Fall back to all-tasks file
    return get_task_from_all_tasks(task_id)


def get_tasks_by_status(status: TaskStatus, use_locking: bool = True) -> List[BackgroundTask]:
    """
    Get all tasks with a specific status.

    Args:
        status: TaskStatus to filter by
        use_locking: Whether to use file locking for thread safety

    Returns:
        List of tasks matching the status
    """
    tasks = get_background_tasks(use_locking=use_locking)
    return [task for task in tasks if task.status == status]


def get_active_tasks(use_locking: bool = True) -> List[BackgroundTask]:
    """
    Get all active (pending or running) tasks.

    Args:
        use_locking: Whether to use file locking for thread safety

    Returns:
        List of active tasks
    """
    tasks = get_background_tasks(use_locking=use_locking)
    return [task for task in tasks if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING)]


def cleanup_expired_tasks(
    retention_hours: float = DEFAULT_RETENTION_HOURS,
    delete_logs: bool = False,
    use_locking: bool = True,
) -> int:
    """
    Remove expired tasks from state and all-tasks file.

    Args:
        retention_hours: Hours to retain completed tasks
        delete_logs: Whether to also delete associated log files
        use_locking: Whether to use file locking for thread safety

    Returns:
        Number of tasks removed
    """
    # Clean up recent tasks
    state = load_state(use_locking=use_locking)
    tasks = _get_recent_tasks_from_state(state)
    initial_count = len(tasks)

    remaining_tasks = []
    expired_tasks = []

    for task in tasks:
        if task.is_expired(retention_hours):
            expired_tasks.append(task)
        else:
            remaining_tasks.append(task)

    # Delete log files if requested
    if delete_logs:
        for task in expired_tasks:
            if task.log_file:
                log_path = Path(task.log_file)
                if log_path.exists():
                    try:
                        log_path.unlink()
                    except OSError:
                        pass

    # Save remaining recent tasks
    _save_recent_tasks_to_state(state, remaining_tasks)
    save_state(state, use_locking=use_locking)

    # Also clean up all-tasks file
    all_tasks_data = _load_all_tasks_file()
    all_tasks = [BackgroundTask.from_dict(t) for t in all_tasks_data]
    remaining_all = [t for t in all_tasks if not t.is_expired(retention_hours)]

    if len(remaining_all) < len(all_tasks):
        _save_all_tasks_file([t.to_dict() for t in remaining_all])

    return initial_count - len(remaining_tasks)


def remove_task(task_id: str, delete_log: bool = False, use_locking: bool = True) -> bool:
    """
    Remove a specific task from state and all-tasks file.

    Args:
        task_id: ID of the task to remove
        delete_log: Whether to also delete the associated log file
        use_locking: Whether to use file locking for thread safety

    Returns:
        True if task was found and removed, False otherwise
    """
    # Remove from recent tasks
    state = load_state(use_locking=use_locking)
    tasks = _get_recent_tasks_from_state(state)

    removed_task = None
    for i, task in enumerate(tasks):
        if task.id == task_id or task.id.startswith(task_id):
            removed_task = tasks.pop(i)
            break

    if removed_task:
        # Delete log file if requested
        if delete_log and removed_task.log_file:
            log_path = Path(removed_task.log_file)
            if log_path.exists():
                try:
                    log_path.unlink()
                except OSError:
                    pass

        _save_recent_tasks_to_state(state, tasks)
        save_state(state, use_locking=use_locking)

    # Also remove from all-tasks file
    all_tasks_data = _load_all_tasks_file()
    original_len = len(all_tasks_data)
    all_tasks_data = [t for t in all_tasks_data if not (t.get("id") == task_id or t.get("id", "").startswith(task_id))]

    if len(all_tasks_data) < original_len:
        _save_all_tasks_file(all_tasks_data)
        return True

    return removed_task is not None


# =============================================================================
# Background Task Tracking Output
# =============================================================================


def get_other_incomplete_tasks(exclude_task_id: str) -> List[BackgroundTask]:
    """
    Get incomplete tasks from recent tasks, excluding the specified task.

    Args:
        exclude_task_id: Task ID to exclude from the list

    Returns:
        List of incomplete BackgroundTask objects (not completed, not the excluded one)
    """
    tasks = get_recent_tasks()
    incomplete = []
    for task in tasks:
        if task.id != exclude_task_id and task.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            incomplete.append(task)
    return incomplete


def get_most_recent_tasks_per_command() -> Dict[str, BackgroundTask]:
    """
    Get the most recent task for each command type.

    Returns:
        Dictionary mapping command name to the most recent BackgroundTask for that command.
        Tasks are sorted by start time (most recent first).
    """
    tasks = get_recent_tasks()
    most_recent: Dict[str, BackgroundTask] = {}

    # Tasks are already sorted by start time (most recent first) from get_recent_tasks
    for task in tasks:
        if task.command not in most_recent:
            most_recent[task.command] = task

    return most_recent


def get_incomplete_most_recent_per_command(exclude_task_id: str = "") -> List[BackgroundTask]:
    """
    Get incomplete tasks that are the most recent of their command type.

    This filters to only tasks that:
    1. Are the most recent task for their command type
    2. Are not completed or failed (i.e., still running or pending)
    3. Are not the excluded task ID

    Args:
        exclude_task_id: Task ID to exclude from results

    Returns:
        List of incomplete BackgroundTask objects that are most-recent-per-command
    """
    most_recent = get_most_recent_tasks_per_command()
    incomplete = []

    for task in most_recent.values():
        if task.id != exclude_task_id and task.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            incomplete.append(task)

    return incomplete


def get_failed_most_recent_per_command(
    exclude_task_id: str = "",
    exclude_commands: Optional[List[str]] = None,
) -> List[BackgroundTask]:
    """
    Get failed tasks that are the most recent of their command type.

    This identifies commands where the most recent execution failed.

    Args:
        exclude_task_id: Task ID to exclude from results
        exclude_commands: List of command names to exclude entirely (e.g., if a more
            recent task with that command succeeded, we don't want to report the
            older failed task)

    Returns:
        List of failed BackgroundTask objects that are most-recent-per-command
    """
    most_recent = get_most_recent_tasks_per_command()
    failed = []
    exclude_commands = exclude_commands or []

    for task in most_recent.values():
        if task.id == exclude_task_id:
            continue
        if task.command in exclude_commands:
            continue
        if task.status == TaskStatus.FAILED:
            failed.append(task)

    return failed


def print_task_tracking_info(task: BackgroundTask, action_description: Optional[str] = None) -> None:
    """
    Print standardized tracking information for a background task.

    This function:
    1. Automatically sets background.task_id in state
    2. Prints the task started message with command and ID
    3. Prints simple instruction to wait for completion

    Args:
        task: The BackgroundTask that was just started
        action_description: Optional description of what the task is doing.
                           If not provided, defaults to "Running {command} command"
    """
    from .state import set_value

    # Automatically set the task_id in state
    set_value("background.task_id", task.id)

    # Auto-generate description if not provided
    if action_description is None:
        action_description = f"Running {task.command} command"

    # Print header
    print()
    print(
        f"Background task started (command: {task.command}, id: {task.id}), "
        f"task_id automatically set in dfly-state.json for progress tracking."
    )
    print()
    print(f"{action_description}...")
    print()

    # Simple instruction - dfly-task-wait handles everything now
    print("Wait for completion and get next instructions:")
    print("  dfly-task-wait")
