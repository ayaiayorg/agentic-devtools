"""
State management for the agentic-devtools CLI.

Runtime state is stored in ``state.json`` under the active workflow
directory (resolved by ``get_state_dir()``).  A bootstrap file
(``runtime-bootstrap.json``) at ``{git_root}/.agdt/`` records the
current identity and worktree key so ``get_state_dir()`` can build
the scoped path without reading the state file itself.

Key design decisions:
- Single JSON file for workflow state
- Direct parameter passing (no replacement tokens needed!)
- Multiline content works natively in Python CLI
- Auto-approvable commands in VS Code
- File locking to prevent race conditions between concurrent tasks
- Background task tracking via background.recentTasks namespace
"""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .file_locking import FileLockError, locked_state_file

STATE_FILENAME = "state.json"

BOOTSTRAP_FILENAME = "runtime-bootstrap.json"
IDENTITY_OWNER_FILENAME = ".identity-owner"

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


def _resolve_identity(git_root: Optional[Path] = None) -> str:
    """Derive a compact, collision-resistant identity string from git email.

    Algorithm:
    - Read ``git config user.email``, take the local part (before ``@``).
    - Split on ``.``, ``-``, ``_`` to extract name parts (lowercased).
    - Initial candidate: ``first_part[0] + last_part[0:2]`` (3 chars).
      Single-part names use first 3 chars.  Very short parts use all chars.
    - Scan existing directories under ``{git_root}/.agdt/workflows/`` and read
      ``.identity-owner`` files to detect collisions (same candidate but
      different email).
    - On collision: try extending last name by 1 char and first name by 1 char,
      pick whichever produces a shorter unique result (prefer last name on tie).
    - If all chars exhausted: append numeric suffix ``1``, ``2``, … until unique.

    Returns ``"default"`` when ``git config user.email`` is unavailable.
    """
    if git_root is None:
        git_root = _get_git_repo_root()
    if git_root is None:
        return "default"

    email = _get_git_email()

    if not email:
        return "default"

    local_part = email.split("@")[0].lower()
    name_parts = re.split(r"[.\-_]", local_part)
    name_parts = [p for p in name_parts if p]

    if not name_parts:
        return "default"

    first = name_parts[0]
    last = name_parts[-1] if len(name_parts) > 1 else first

    # Build initial candidate (3 chars when possible)
    if len(name_parts) == 1:
        candidate = first[:3]
    else:
        candidate = first[0] + last[:2]

    if not candidate:
        return "default"  # pragma: no cover – defensive; name_parts is non-empty

    # Build owner map from existing identity directories.
    # Directories *without* a ``.identity-owner`` file are treated as claimed
    # by an unknown agent (empty-string sentinel) to avoid cross-agent
    # collisions with pre-existing or manually-created directories.
    workflows_dir = git_root / ".agdt" / "workflows"
    owner_map: Dict[str, str] = {}  # directory name -> email (or "" for unclaimed)
    if workflows_dir.is_dir():
        for entry in workflows_dir.iterdir():
            if entry.is_dir():
                owner_file = entry / IDENTITY_OWNER_FILENAME
                if owner_file.is_file():
                    try:
                        owner_map[entry.name] = owner_file.read_text(encoding="utf-8").strip()
                    except OSError:
                        # Treat unreadable owner files as unclaimed (collision)
                        owner_map[entry.name] = ""
                else:
                    # No owner file → treat as claimed by unknown agent
                    owner_map[entry.name] = ""

    def _is_collision(cand: str) -> bool:
        return cand in owner_map and owner_map[cand] != email

    if not _is_collision(candidate):
        return candidate

    # Collision resolution: try extending from last name / first name
    first_idx = 1  # chars consumed from first name (already used [0])
    last_idx = 2 if len(name_parts) > 1 else 3  # chars consumed from last name

    max_iters = len(first) + len(last) + 10  # safety bound
    for _ in range(max_iters):
        opt_a: Optional[str] = None
        opt_b: Optional[str] = None

        # Option A: extend last name
        if last_idx < len(last):
            opt_a = first[:first_idx] + last[: last_idx + 1] if len(name_parts) > 1 else first[: last_idx + 1]
        # Option B: extend first name
        if first_idx < len(first) and len(name_parts) > 1:
            opt_b = first[: first_idx + 1] + last[:last_idx]

        # Evaluate which option is unique
        a_unique = opt_a is not None and not _is_collision(opt_a)
        b_unique = opt_b is not None and not _is_collision(opt_b)

        if a_unique and b_unique:
            # Both unique — pick shorter; prefer A (last name) on tie
            if len(opt_a) <= len(opt_b):  # type: ignore[arg-type]
                return opt_a  # type: ignore[return-value]
            return opt_b  # type: ignore[return-value]  # pragma: no cover – opt_a/opt_b same length at equal indices
        elif a_unique:
            last_idx += 1
            return opt_a  # type: ignore[return-value]
        elif b_unique:
            first_idx += 1
            return opt_b  # type: ignore[return-value]
        else:
            # Neither unique — advance both indices and keep trying
            if opt_a is not None:
                last_idx += 1
                candidate = opt_a
            if opt_b is not None:
                first_idx += 1
                candidate = opt_b
            if opt_a is None and opt_b is None:
                break  # all chars exhausted

    # Numeric fallback
    base = candidate
    for n in range(1, 10000):
        candidate = f"{base}{n}"
        if not _is_collision(candidate):
            return candidate

    return "default"  # pragma: no cover


def get_bootstrap_state() -> Dict[str, str]:
    """Read the bootstrap file at ``{git_root}/.agdt/runtime-bootstrap.json``.

    Returns a dict with ``"identity"`` and/or ``"worktree_key"`` keys.
    Returns ``{}`` when the file is missing, malformed, or not in a git repo.

    This function must NOT call ``get_state_dir()`` or ``load_state()`` to
    avoid circular dependency.
    """
    git_root = _get_git_repo_root()
    if git_root is None:
        return {}

    bootstrap_path = git_root / ".agdt" / BOOTSTRAP_FILENAME
    try:
        content = bootstrap_path.read_text(encoding="utf-8")
        data = json.loads(content)
        if not isinstance(data, dict):
            return {}
        # Only expose the documented keys and normalize their values.
        # Keys whose stripped value is empty are omitted so callers can
        # treat a missing key as "unset" without checking for "".
        result: Dict[str, str] = {}
        for key in ("identity", "worktree_key"):
            value = data.get(key)
            if isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    result[key] = stripped
        return result
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {}


def _get_git_email() -> str:
    """Return the email from ``git config user.email`` or ``""``."""
    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (FileNotFoundError, OSError):
        return ""


def set_bootstrap_state(
    identity: Optional[str] = None,
    worktree_key: Optional[str] = None,
) -> None:
    """Write (or update) the bootstrap file at ``{git_root}/.agdt/runtime-bootstrap.json``.

    If *identity* is ``None`` it is resolved via ``_resolve_identity()``.
    Existing fields not being updated are preserved.
    Also writes ``.identity-owner`` under ``.agdt/workflows/{identity}/``.

    Silent no-op when not in a git repo.
    """
    git_root = _get_git_repo_root()
    if git_root is None:
        return

    # Read existing bootstrap to preserve documented fields
    bootstrap_path = git_root / ".agdt" / BOOTSTRAP_FILENAME
    existing: Dict[str, str] = {}
    try:
        content = bootstrap_path.read_text(encoding="utf-8")
        data = json.loads(content)
        if isinstance(data, dict):
            for bk in ("identity", "worktree_key"):
                bv = data.get(bk)
                if isinstance(bv, str):
                    stripped = bv.strip()
                    if stripped:
                        existing[bk] = stripped
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError, OSError):
        pass

    # Normalize caller-provided identity: must be str, stripped, non-empty
    if identity is not None:
        if isinstance(identity, str):
            identity = identity.strip() or None
        else:
            identity = None  # Non-str values treated as unset

    # Resolve identity if not provided (or normalized to None)
    if identity is None:
        identity = existing.get("identity") or _resolve_identity(git_root)

    # Normalize caller-provided worktree_key: must be str, stripped, non-empty
    effective_wk: Optional[str] = None
    if worktree_key is not None:
        if isinstance(worktree_key, str):
            stripped_wk = worktree_key.strip()
            if stripped_wk:
                effective_wk = stripped_wk
        # Non-str or whitespace-only worktree_key → treated as deletion

    # Update existing dict (pop invalid/empty keys to stay consistent
    # with get_bootstrap_state() which omits empty-after-strip values)
    if identity:
        existing["identity"] = identity
    else:
        existing.pop("identity", None)

    if worktree_key is not None:
        if effective_wk is not None:
            existing["worktree_key"] = effective_wk
        else:
            existing.pop("worktree_key", None)

    # Write bootstrap file
    bootstrap_path.parent.mkdir(parents=True, exist_ok=True)
    bootstrap_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    # Ensure .agdt/.gitignore exists (silent — no user-facing message here)
    from agentic_devtools.agdt_gitignore import ensure_agdt_gitignore

    ensure_agdt_gitignore(git_root)

    # Write .identity-owner file
    if identity:
        identity_dir = git_root / ".agdt" / "workflows" / identity
        identity_dir.mkdir(parents=True, exist_ok=True)
        owner_file = identity_dir / IDENTITY_OWNER_FILENAME
        email = _get_git_email()
        if email:
            owner_file.write_text(email, encoding="utf-8")


def get_state_dir() -> Path:
    """Get the directory for storing the state file.

    Priority:
    1. ``AGENTIC_DEVTOOLS_STATE_DIR`` environment variable
    2. ``DFLY_AI_HELPERS_STATE_DIR`` environment variable (legacy alias)
    3. ``.agdt/workflows/{identity}/{worktree_key}/`` relative to git root
       (identity and worktree_key read from ``.agdt/runtime-bootstrap.json``)
    4. ``.agdt/workflows/_unscoped/`` relative to git root (when bootstrap
       file is missing or incomplete)
    5. ``.agdt-temp/`` in CWD (when not in a git repo)
    """
    # 1/2. Environment variable override (primary + legacy alias)
    env_dir = os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR") or os.environ.get("DFLY_AI_HELPERS_STATE_DIR")
    if env_dir:
        path = Path(env_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    # 2/3. Git-based resolution
    git_root = _get_git_repo_root()
    if git_root:
        # Read bootstrap inline to avoid a second _get_git_repo_root() call
        # (get_bootstrap_state() would call _get_git_repo_root() again).
        bootstrap_path = git_root / ".agdt" / BOOTSTRAP_FILENAME
        bootstrap: Dict[str, Any] = {}
        try:
            if bootstrap_path.is_file():
                bootstrap = json.loads(bootstrap_path.read_text(encoding="utf-8"))
                if not isinstance(bootstrap, dict):
                    bootstrap = {}
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            bootstrap = {}

        # Validate types to match get_bootstrap_state()'s strict filtering;
        # non-string values (e.g. {"identity": 123}) fall back to _unscoped
        # rather than coercing to unexpected directory names.
        raw_id = bootstrap.get("identity", "")
        raw_wk = bootstrap.get("worktree_key", "")
        identity = raw_id.strip() if isinstance(raw_id, str) else ""
        worktree_key = raw_wk.strip() if isinstance(raw_wk, str) else ""

        if identity and worktree_key:
            scoped = git_root / ".agdt" / "workflows" / identity / worktree_key
            scoped.mkdir(parents=True, exist_ok=True)
            return scoped

        unscoped = git_root / ".agdt" / "workflows" / "_unscoped"
        unscoped.mkdir(parents=True, exist_ok=True)
        return unscoped

    # 4. Final fallback — not in a git repo
    fallback = Path.cwd() / ".agdt-temp"
    fallback.mkdir(exist_ok=True)
    return fallback


def get_state_file_path() -> Path:
    """Get the full path to the state JSON file."""
    return get_state_dir() / STATE_FILENAME


def _update_bootstrap_worktree_key(worktree_key: str) -> None:
    """Update the ``worktree_key`` in the bootstrap file, creating it if needed.

    Unlike ``set_bootstrap_state()``, this does **not** call ``subprocess``
    (no ``_get_git_repo_root`` / ``_resolve_identity``).  It locates the
    bootstrap file by walking up from a subprocess-free base directory:
    either ``AGENTIC_DEVTOOLS_STATE_DIR`` / ``DFLY_AI_HELPERS_STATE_DIR``
    (when set) or the current working directory, looking for a ``.agdt``
    directory.

    If the bootstrap file does not exist but the ``.agdt/`` directory does,
    the file is created with just ``{"worktree_key": ...}``.  Identity will
    be resolved on the next ``set_bootstrap_state()`` call; until then,
    ``get_state_dir()`` falls back to ``_unscoped``.

    This exists so that ``set_value()`` can keep the bootstrap in sync
    without interfering with tests that globally mock ``subprocess.run``.
    """
    try:
        # Choose a subprocess-free starting point (same priority as
        # get_state_dir()'s env-var check):
        # 1. AGENTIC_DEVTOOLS_STATE_DIR (primary)
        # 2. DFLY_AI_HELPERS_STATE_DIR (legacy alias)
        # 3. Current working directory as a reasonable default inside the repo
        env_dir = os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR") or os.environ.get("DFLY_AI_HELPERS_STATE_DIR")
        if env_dir:
            base_dir = Path(env_dir)
        else:
            base_dir = Path.cwd()

        # Walk up from base_dir to find .agdt/
        for parent in [base_dir] + list(base_dir.parents):
            agdt_dir = parent / ".agdt"
            bootstrap_path = agdt_dir / BOOTSTRAP_FILENAME
            if bootstrap_path.is_file():
                content = bootstrap_path.read_text(encoding="utf-8")
                data = json.loads(content)
                if isinstance(data, dict):
                    data["worktree_key"] = worktree_key
                    bootstrap_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                return
            if agdt_dir.is_dir():
                # .agdt/ exists but no bootstrap file yet — create it with
                # just the worktree_key so subsequent calls can update it.
                bootstrap_path.write_text(
                    json.dumps({"worktree_key": worktree_key}, indent=2),
                    encoding="utf-8",
                )
                return
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        pass


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


def save_state(
    state: Dict[str, Any],
    use_locking: bool = False,
    lock_timeout: float = DEFAULT_LOCK_TIMEOUT,
) -> Path:
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

    # Signal that workflow state has been mutated.  The CLI runner calls
    # persist_if_dirty() after every command to commit pending changes to
    # the -agdt branch automatically.
    try:
        from .cli.git.agdt_branch import mark_dirty

        mark_dirty()
    except ImportError:  # pragma: no cover
        pass  # agdt_branch not available (e.g., minimal install)

    # Keep bootstrap in sync when context keys change.
    # Uses _update_bootstrap_worktree_key (subprocess-free) to avoid
    # consuming mock side_effects in tests that globally patch subprocess.run.
    try:
        if key == "jira.issue_key":
            # Only accept non-empty strings as issue keys to avoid writing
            # unintended values (e.g., dict/list) into the bootstrap file.
            if isinstance(value, str):
                issue_key = value.strip()
                if issue_key:
                    _update_bootstrap_worktree_key(issue_key)
        elif key == "pull_request_id":
            # Only accept int or digit-only string PR ids.
            # Use ``type(value) is int`` instead of ``isinstance(value, int)``
            # because bool is a subclass of int — ``isinstance(True, int)``
            # is True, which would write "PR1" / "PR0" for booleans.
            pr_id_str: Optional[str] = None
            if type(value) is int:  # noqa: E721
                pr_id_str = str(value)
            elif isinstance(value, str):
                candidate = value.strip()
                if candidate.isdigit():
                    pr_id_str = candidate
            if pr_id_str:
                _update_bootstrap_worktree_key(f"PR{pr_id_str}")
    except Exception:  # noqa: BLE001 – bootstrap failure is non-fatal
        pass


# Context-switching keys that may trigger cross-lookup
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
    1. Atomically updates the value and deletes the counterpart key in a
       single load/save cycle to prevent stale data
    2. Optionally triggers a background cross-lookup for the related key

    Cross-lookup behavior:
    - pull_request_id change -> looks up jira.issue_key from PR source branch/title
    - jira.issue_key change -> looks up pull_request_id from Jira/Azure DevOps

    Args:
        key: Must be "pull_request_id" or "jira.issue_key"
        value: The new value to set
        trigger_cross_lookup: If True, start background task to find related key
        verbose: If True, print status messages

    Returns:
        True if the value changed, False if unchanged

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

    # Value is changing — update it directly
    if verbose:
        if current_value is not None:
            print(f"🔄 Context switch: {key} changing from {current_value} to {value}")
        else:
            print(f"🔄 Setting context: {key} = {value}")

    # Atomic update: set the new key and clear the stale counterpart in a
    # single load/save cycle to prevent a transient on-disk state where both
    # context keys exist (which could cause incorrect worktree key resolution
    # since jira.issue_key has higher priority than pull_request_id in
    # resolve_worktree_key).  Cross-lookup will repopulate the counterpart.
    counterpart = "jira.issue_key" if key == "pull_request_id" else "pull_request_id"
    state = load_state()

    # Set the new context key (supports dot notation for jira.issue_key)
    parts = key.split(".")
    if len(parts) == 1:
        state[key] = value
    else:
        current = state
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    # Delete counterpart (supports dot notation for jira.issue_key)
    cp_parts = counterpart.split(".")
    if len(cp_parts) == 1:
        state.pop(counterpart, None)
    else:
        cp_current = state
        for cp_part in cp_parts[:-1]:
            if not isinstance(cp_current, dict) or cp_part not in cp_current:
                break
            cp_current = cp_current[cp_part]
        else:
            if isinstance(cp_current, dict):
                cp_current.pop(cp_parts[-1], None)

    save_state(state)

    # Signal that workflow state has been mutated.  The CLI runner calls
    # persist_if_dirty() after every command to commit pending changes to
    # the -agdt branch automatically.
    try:
        from .cli.git.agdt_branch import mark_dirty

        mark_dirty()
    except ImportError:  # pragma: no cover
        pass  # agdt_branch not available (e.g., minimal install)

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


def clear_state() -> None:
    """
    Clear all state by writing an empty JSON file.

    This resets the state file contents but does NOT delete directories
    or other files in the state directory.  Use sparingly — most callers
    should use delete_value() for targeted key removal instead.
    """
    save_state({})


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


def get_pypi_package_name(required: bool = False) -> Optional[str]:
    """Get the PyPI package name from state."""
    value = get_value("pypi.package_name", required=required)
    return str(value) if value is not None else None


def set_pypi_package_name(package_name: str) -> None:
    """Set the PyPI package name in state."""
    set_value("pypi.package_name", package_name)


def get_pypi_version(required: bool = False) -> Optional[str]:
    """Get the PyPI version from state."""
    value = get_value("pypi.version", required=required)
    return str(value) if value is not None else None


def set_pypi_version(version: str) -> None:
    """Set the PyPI version in state."""
    set_value("pypi.version", version)


def get_pypi_repository(required: bool = False) -> Optional[str]:
    """Get the PyPI repository from state (pypi/testpypi)."""
    value = get_value("pypi.repository", required=required)
    return str(value) if value is not None else None


def set_pypi_repository(repository: str) -> None:
    """Set the PyPI repository in state (pypi/testpypi)."""
    set_value("pypi.repository", repository)


def get_pypi_dry_run() -> bool:
    """Check if the PyPI dry-run mode is enabled."""
    value = get_value("pypi.dry_run")
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes")


def set_pypi_dry_run(enabled: bool) -> None:
    """Set the PyPI dry-run mode."""
    set_value("pypi.dry_run", enabled)


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
