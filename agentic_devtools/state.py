"""
State management using a single JSON file.

All AI helper state is stored in a single JSON file (agdt-state.json),
making it easy to inspect, debug, and manage state across commands.

Key design decisions:
- Single JSON file instead of multiple temp files
- Direct parameter passing (no replacement tokens needed!)
- Multiline content works natively in Python CLI
- Auto-approvable commands in VS Code
- File locking to prevent race conditions between concurrent tasks
- Background task tracking via backgroundTasks property
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .file_locking import FileLockError, locked_state_file

STATE_FILENAME = "agdt-state.json"

# Default lock timeout in seconds
DEFAULT_LOCK_TIMEOUT = 5.0


def _get_git_repo_root() -> Optional[Path]:
    """
    Get the git repository or worktree root using git rev-parse.

    This reliably finds the root of the current repo or worktree,
    regardless of how deep in the directory tree we are.

    Returns:
        Path to the repo/worktree root, or None if not in a git repo.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
    except (FileNotFoundError, OSError):
        pass
    return None


def get_state_dir() -> Path:
    """
    Get the directory for storing the state file.

    Priority:
    1. AGENTIC_DEVTOOLS_STATE_DIR environment variable
    2. DFLY_AI_HELPERS_STATE_DIR environment variable (legacy)
    3. scripts/temp relative to git repo/worktree root (auto-detected via git)
    4. scripts/temp found by walking up from cwd (fallback if not in git repo)
    5. Current working directory / .agdt-temp (final fallback)

    The function uses `git rev-parse --show-toplevel` to reliably find the
    repo/worktree root, which works correctly even in deep subdirectories
    and in git worktrees.
    """
    # Check environment variable first
    env_dir = os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR") or os.environ.get("DFLY_AI_HELPERS_STATE_DIR")
    if env_dir:
        path = Path(env_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    # Try to find repo root via git (works for both main repo and worktrees)
    git_root = _get_git_repo_root()
    if git_root:
        scripts_dir = git_root / "scripts"
        if scripts_dir.is_dir():
            scripts_temp = scripts_dir / "temp"
            scripts_temp.mkdir(exist_ok=True)
            return scripts_temp

    # Fallback: Walk up from cwd looking for scripts directory
    # (for cases where git is not available)
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        scripts_dir = parent / "scripts"
        if scripts_dir.is_dir():
            # Found scripts directory - use or create scripts/temp
            scripts_temp = scripts_dir / "temp"
            scripts_temp.mkdir(exist_ok=True)
            return scripts_temp
        # Also check if we're inside a scripts directory
        if parent.name == "scripts" and parent.is_dir():
            temp_dir = parent / "temp"
            temp_dir.mkdir(exist_ok=True)
            return temp_dir

    # Final fallback to .agdt-temp in cwd
    fallback = cwd / ".agdt-temp"
    fallback.mkdir(exist_ok=True)
    return fallback


def get_state_file_path() -> Path:
    """Get the full path to the state JSON file."""
    return get_state_dir() / STATE_FILENAME


def load_state(use_locking: bool = False, lock_timeout: float = DEFAULT_LOCK_TIMEOUT) -> Dict[str, Any]:
    """
    Load the current state from the JSON file.

    Args:
        use_locking: If True, acquire a shared lock before reading (for concurrent access safety)
        lock_timeout: Maximum time to wait for lock in seconds

    Returns:
        Dictionary of all state values, empty dict if file doesn't exist
    """
    path = get_state_file_path()

    if not path.exists():
        return {}

    try:
        if use_locking:
            with locked_state_file(path, timeout=lock_timeout) as f:
                content = f.read()
                return json.loads(content) if content.strip() else {}
        else:
            content = path.read_text(encoding="utf-8")
            return json.loads(content) if content.strip() else {}
    except json.JSONDecodeError:
        return {}
    except FileLockError:
        # If we can't acquire lock, fall back to unlocked read
        content = path.read_text(encoding="utf-8")
        return json.loads(content) if content.strip() else {}


def save_state(state: Dict[str, Any], use_locking: bool = False, lock_timeout: float = DEFAULT_LOCK_TIMEOUT) -> Path:
    """
    Save the state dictionary to the JSON file.

    Args:
        state: Dictionary of state values
        use_locking: If True, acquire an exclusive lock before writing (for concurrent access safety)
        lock_timeout: Maximum time to wait for lock in seconds

    Returns:
        Path to the state file
    """
    path = get_state_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    content = json.dumps(state, indent=2, ensure_ascii=False)

    if use_locking:
        try:
            with locked_state_file(path, timeout=lock_timeout) as f:
                f.seek(0)
                f.write(content)
                f.truncate()
        except FileLockError:
            # If we can't acquire lock, fall back to unlocked write
            path.write_text(content, encoding="utf-8")
    else:
        path.write_text(content, encoding="utf-8")

    return path


def load_state_locked(lock_timeout: float = DEFAULT_LOCK_TIMEOUT) -> Dict[str, Any]:
    """
    Load state with file locking enabled.

    Convenience function for operations that need concurrent access safety.

    Args:
        lock_timeout: Maximum time to wait for lock in seconds

    Returns:
        Dictionary of all state values
    """
    return load_state(use_locking=True, lock_timeout=lock_timeout)


def save_state_locked(state: Dict[str, Any], lock_timeout: float = DEFAULT_LOCK_TIMEOUT) -> Path:
    """
    Save state with file locking enabled.

    Convenience function for operations that need concurrent access safety.

    Args:
        state: Dictionary of state values
        lock_timeout: Maximum time to wait for lock in seconds

    Returns:
        Path to the state file
    """
    return save_state(state, use_locking=True, lock_timeout=lock_timeout)


def get_value(key: str, required: bool = False) -> Optional[Any]:
    """
    Get a value from state by key.

    Supports dot notation for nested keys:
    - 'pull_request_id' -> state['pull_request_id']
    - 'jira.summary' -> state['jira']['summary']

    Args:
        key: State key (e.g., 'pull_request_id', 'jira.summary')
        required: If True, raise error when key doesn't exist

    Returns:
        Value or None if not found
    """
    state = load_state()

    # Support dot notation for nested keys
    parts = key.split(".")
    current = state

    for part in parts:
        if not isinstance(current, dict) or part not in current:
            if required:
                raise KeyError(f"Required state key not found: {key}")
            return None
        current = current[part]

    return current


def set_value(key: str, value: Any) -> None:
    """
    Set a value in state.

    Supports dot notation for nested keys:
    - 'pull_request_id' -> state['pull_request_id'] = value
    - 'jira.summary' -> state['jira']['summary'] = value

    Args:
        key: State key (e.g., 'pull_request_id', 'jira.summary')
        value: Value to store (can be any JSON-serializable type)
    """
    state = load_state()

    # Support dot notation for nested keys
    parts = key.split(".")

    if len(parts) == 1:
        # Simple key
        state[key] = value
    else:
        # Nested key - traverse and create intermediate dicts as needed
        current = state
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    save_state(state)


# Context-switching keys that trigger temp folder clearing
CONTEXT_SWITCH_KEYS = {"pull_request_id", "jira.issue_key"}


def set_context_value(
    key: str,
    value: Any,
    trigger_cross_lookup: bool = True,
    verbose: bool = True,
) -> bool:
    """
    Set a context-switching value (pull_request_id or jira.issue_key).

    When one of these primary context keys changes to a NEW value:
    1. Clears the entire temp folder (preserving the new value)
    2. Optionally triggers a background cross-lookup for the related key

    This ensures that switching to a new PR or Jira issue starts with a clean slate,
    removing all temp files, prompts, and queues from the previous context.

    Cross-lookup behavior:
    - pull_request_id change -> looks up jira.issue_key from PR source branch/title
    - jira.issue_key change -> looks up pull_request_id from Jira/Azure DevOps

    Args:
        key: Must be "pull_request_id" or "jira.issue_key"
        value: The new value to set
        trigger_cross_lookup: If True, start background task to find related key
        verbose: If True, print status messages

    Returns:
        True if the value changed (and temp was cleared), False if unchanged

    Raises:
        ValueError: If key is not a context-switching key
    """
    if key not in CONTEXT_SWITCH_KEYS:
        raise ValueError(f"set_context_value only accepts: {CONTEXT_SWITCH_KEYS}")

    # Normalize value for comparison (convert to string for consistency)
    normalized_value = str(value) if value is not None else None

    # Get current value
    current_value = get_value(key)
    current_normalized = str(current_value) if current_value is not None else None

    # If value hasn't changed, just return (no clearing needed)
    if normalized_value == current_normalized:
        if verbose:
            print(f"ℹ️  {key} unchanged (already set to {value})")
        return False

    # Value is changing - clear temp folder but preserve the new context value
    if verbose:
        if current_value is not None:
            print(f"🔄 Context switch: {key} changing from {current_value} to {value}")
        else:
            print(f"🔄 Setting context: {key} = {value}")
        print("✓ Clearing temp folder for fresh context...")

    # Build preserved state with the new value
    # Note: The elif branch below is guaranteed to be True after the if-branch is False
    # because set_context_value validates that key must be one of these two values.
    # This makes the 333->336 branch (elif=False) unreachable.
    preserve = {}
    if key == "pull_request_id":
        preserve["pull_request_id"] = value
    elif key == "jira.issue_key":  # pragma: no branch
        preserve["jira"] = {"issue_key": value}

    clear_temp_folder(preserve_keys=preserve)

    # Trigger cross-lookup in background if requested
    if trigger_cross_lookup:
        _trigger_cross_lookup(key, value, verbose)

    return True


def _trigger_cross_lookup(key: str, value: Any, verbose: bool = True) -> None:
    """
    Trigger a background task to find the related context key.

    Args:
        key: The key that was just set ("pull_request_id" or "jira.issue_key")
        value: The value that was set
        verbose: Whether to print status messages
    """
    if key == "pull_request_id":
        # PR ID was set -> look up the Jira issue key from PR details
        if verbose:
            print(f"🔍 Starting background lookup for Jira issue from PR #{value}...")
        _start_jira_lookup_from_pr(int(value))

    elif key == "jira.issue_key":
        # Jira issue key was set -> look up the PR ID
        if verbose:
            print(f"🔍 Starting background lookup for PR from Jira issue {value}...")
        _start_pr_lookup_from_jira(str(value))


def _start_jira_lookup_from_pr(pull_request_id: int) -> None:
    """
    Start a background task to find Jira issue key from a PR.

    Extracts issue key from PR source branch name (e.g., feature/DFLY-1234/...).
    """
    try:
        from .cli.azure_devops.async_commands import lookup_jira_issue_from_pr_async

        lookup_jira_issue_from_pr_async(pull_request_id)
    except ImportError:
        # Silently fail if async module not available
        pass
    except Exception:
        # Don't let lookup failures break the main flow
        pass


def _start_pr_lookup_from_jira(issue_key: str) -> None:
    """
    Start a background task to find PR from a Jira issue key.

    Searches for PR linked in Jira comments or by branch name.
    """
    try:
        from .cli.azure_devops.async_commands import lookup_pr_from_jira_issue_async

        lookup_pr_from_jira_issue_async(issue_key)
    except ImportError:
        # Silently fail if async module not available
        pass
    except Exception:
        # Don't let lookup failures break the main flow
        pass


def delete_value(key: str) -> bool:
    """
    Delete a value from state.

    Supports dot notation for nested keys:
    - 'pull_request_id' -> deletes state['pull_request_id']
    - 'jira.summary' -> deletes state['jira']['summary']

    Returns:
        True if key was deleted, False if it didn't exist
    """
    state = load_state()

    # Support dot notation for nested keys
    parts = key.split(".")

    if len(parts) == 1:
        # Simple key
        if key in state:
            del state[key]
            save_state(state)
            return True
        return False
    else:
        # Nested key - traverse to parent
        current = state
        for part in parts[:-1]:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]

        final_key = parts[-1]
        if isinstance(current, dict) and final_key in current:
            del current[final_key]
            save_state(state)
            return True
        return False


def clear_temp_folder(preserve_keys: Optional[Dict[str, Any]] = None) -> None:
    """
    Clear the entire temp folder, removing all state and temporary files.

    This removes:
    - agdt-state.json (the state file)
    - pull-request-review/ (PR review queue and prompts)
    - background-tasks/ (background task state)
    - All temp-*.json and temp-*.md files

    Note: The Jira CA bundle (jira_ca_bundle.pem) is now stored in scripts/
    (version-controlled), not in temp/, so it won't be affected by clearing.

    Args:
        preserve_keys: Optional dict of state keys to preserve after clearing.
                      These will be written to a fresh state file.
    """
    import shutil

    temp_dir = get_state_dir()

    if temp_dir.exists():
        # Delete everything in the temp folder
        for item in temp_dir.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            except OSError:
                # Ignore errors (file in use, permission issues, etc.)
                pass
    else:
        # Create the temp directory if it doesn't exist
        temp_dir.mkdir(parents=True, exist_ok=True)

    # Restore preserved keys to fresh state file if provided
    if preserve_keys:
        save_state(preserve_keys)


def clear_state() -> None:
    """
    Clear all state by removing the entire temp folder contents.

    This is now an alias for clear_temp_folder() for backward compatibility.
    """
    clear_temp_folder()


def get_all_keys() -> List[str]:
    """Get list of all keys in state."""
    return list(load_state().keys())


# Convenience functions for common parameters


def get_pull_request_id(required: bool = False) -> Optional[int]:
    """Get the pull request ID from state."""
    value = get_value("pull_request_id", required=required)
    return int(value) if value is not None else None


def set_pull_request_id(pull_request_id: int) -> None:
    """Set the pull request ID in state."""
    set_value("pull_request_id", pull_request_id)


def get_thread_id(required: bool = False) -> Optional[int]:
    """Get the thread ID from state."""
    value = get_value("thread_id", required=required)
    return int(value) if value is not None else None


def set_thread_id(thread_id: int) -> None:
    """Set the thread ID in state."""
    set_value("thread_id", thread_id)


def is_dry_run() -> bool:
    """Check if dry run mode is enabled."""
    value = get_value("dry_run")
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes")


def set_dry_run(enabled: bool) -> None:
    """Set dry run mode."""
    set_value("dry_run", enabled)


def should_resolve_thread() -> bool:
    """Check if thread should be resolved after reply."""
    value = get_value("resolve_thread")
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes")


def set_resolve_thread(enabled: bool) -> None:
    """Set whether to resolve thread after reply."""
    set_value("resolve_thread", enabled)


# Workflow state management


def get_workflow_state() -> Optional[Dict[str, Any]]:
    """
    Get the current workflow state.

    Returns:
        Dictionary with workflow state or None if no workflow is active.
        Structure: {
            "active": str,          # Workflow name (e.g., "pull-request-review")
            "status": str,          # Status (e.g., "initiated", "in-progress", "completed")
            "step": str,            # Current step name (e.g., "initiate", "review-file")
            "started_at": str,      # ISO timestamp when workflow started
            "context": dict         # Workflow-specific context data
        }
    """
    return get_value("workflow")


def set_workflow_state(
    name: str,
    status: str,
    step: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Set the workflow state.

    Args:
        name: Workflow name (e.g., "pull-request-review", "work-on-jira-issue")
        status: Workflow status (e.g., "initiated", "in-progress", "completed")
        step: Current step within the workflow (e.g., "initiate", "review-file")
        context: Workflow-specific context data (e.g., PR ID, Jira key)
    """
    from datetime import datetime, timezone

    # Get existing workflow state to preserve started_at if updating
    existing = get_workflow_state()
    started_at = (
        existing.get("started_at")
        if existing and existing.get("active") == name
        else datetime.now(timezone.utc).isoformat()
    )

    workflow_data: Dict[str, Any] = {
        "active": name,
        "status": status,
        "started_at": started_at,
    }

    if step is not None:
        workflow_data["step"] = step

    if context is not None:
        # Merge with existing context if updating same workflow
        if existing and existing.get("active") == name:
            existing_context = existing.get("context", {})
            merged = {**existing_context, **context}
            # Remove keys explicitly set to None (allows clearing nested values)
            workflow_data["context"] = {k: v for k, v in merged.items() if v is not None}
        else:
            workflow_data["context"] = context
    elif existing and existing.get("active") == name:
        # Preserve existing context if not provided
        workflow_data["context"] = existing.get("context", {})

    set_value("workflow", workflow_data)


def clear_workflow_state() -> None:
    """Clear the workflow state (end the current workflow)."""
    delete_value("workflow")


def is_workflow_active(workflow_name: Optional[str] = None) -> bool:
    """
    Check if a workflow is currently active.

    Args:
        workflow_name: If provided, check if this specific workflow is active.
                      If None, check if any workflow is active.

    Returns:
        True if a workflow (or the specified workflow) is active
    """
    workflow = get_workflow_state()
    if workflow is None:
        return False

    if workflow_name is not None:
        return workflow.get("active") == workflow_name

    return bool(workflow.get("active"))


def update_workflow_step(step: str, status: Optional[str] = None) -> None:
    """
    Update the current workflow step (and optionally status).

    Args:
        step: New step name
        status: New status (defaults to keeping current status)

    Raises:
        ValueError: If no workflow is active
    """
    workflow = get_workflow_state()
    if workflow is None:
        raise ValueError("No workflow is currently active")

    set_workflow_state(
        name=workflow["active"],
        status=status if status is not None else workflow.get("status", "in-progress"),
        step=step,
        context=workflow.get("context"),
    )


def update_workflow_context(context: Dict[str, Any]) -> None:
    """
    Update the workflow context (merges with existing context).

    Args:
        context: Context data to merge

    Raises:
        ValueError: If no workflow is active
    """
    workflow = get_workflow_state()
    if workflow is None:
        raise ValueError("No workflow is currently active")

    set_workflow_state(
        name=workflow["active"],
        status=workflow.get("status", "in-progress"),
        step=workflow.get("step"),
        context=context,
    )
