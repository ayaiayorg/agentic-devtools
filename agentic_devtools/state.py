"""
State management for the agentic-devtools CLI.

Runtime state is stored in ``state.json`` under the active workflow
directory (resolved by ``get_state_dir()``).  A bootstrap file
(``runtime-bootstrap.json``) at ``{git_root}/.agdt/`` records the current
``worktree_key`` so ``get_state_dir()`` can build the scoped path.  The
``identity`` (derived from ``git config user.email`` via ``_resolve_identity()``)
is stored separately in ``{git_root}/.agdt/identity.json`` and is validated
on every workflow start by comparing the cached email against the current
``git config user.email``; it is re-resolved only on mismatch.

Key design decisions:
- Single JSON file for workflow state
- Direct parameter passing (no replacement tokens needed!)
- Multiline content works natively in Python CLI
- Auto-approvable commands in VS Code
- File locking to prevent race conditions between concurrent tasks
- Background task tracking via background.recentTasks namespace
"""

import contextlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, overload

from .file_locking import FileLockError, locked_state_file

STATE_FILENAME = "state.json"

BOOTSTRAP_FILENAME = "runtime-bootstrap.json"
IDENTITY_CACHE_FILENAME = "identity.json"
IDENTITY_OWNER_FILENAME = ".identity-owner"

# Pin file for state directory resolution (race condition fix #1180)
PIN_FILENAME = "pinned-state-dir.json"
RECOGNIZED_PIN_WORKFLOWS: frozenset[str] = frozenset({"pull-request-review"})
DEFAULT_PIN_TTL_HOURS = 24

# Default lock timeout in seconds
DEFAULT_LOCK_TIMEOUT = 5.0

# Module-level flag to emit pin file diagnostic only once per process
_pin_logged = False


def _get_git_repo_root() -> Path | None:
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


def _resolve_identity(git_root: Path | None = None, *, _email: str | None = None) -> str:
    """Derive a compact, collision-resistant identity string from git email.

    Algorithm:
    - Read ``git config user.email``, take the local part (before ``@``).
    - Split on ``.``, ``-``, ``_`` to extract name parts (lowercased).
    - Initial candidate: ``first_part[0] + second_part[0:2]`` (3 chars).
      When the email has 3+ segments, uses the 2nd segment (index 1), not the last.
      Single-part names use first 3 chars.  Very short parts use all chars.
    - Scan existing directories under ``{git_root}/.agdt/workflows/`` and read
      ``.identity-owner`` files to detect collisions (same candidate but
      different email).
    - On collision: try extending second name by 1 char and first name by 1 char,
      pick whichever produces a shorter unique result (prefer second name on tie).
    - If all chars exhausted: append numeric suffix ``1``, ``2``, … until unique.

    Returns ``"default"`` when ``git config user.email`` is unavailable.

    *_email* is an optional keyword-only argument.  When provided it is used
    directly, avoiding a second ``git config user.email`` subprocess call.
    Callers that have already fetched the email (e.g. ``_get_or_refresh_identity``)
    should pass it here to eliminate redundant subprocess overhead.
    """
    if git_root is None:
        git_root = _get_git_repo_root()
    if git_root is None:
        return "default"

    # Use the caller-supplied email when available to avoid a second subprocess call
    email = _email if _email is not None else _get_git_email()

    if not email:
        return "default"

    local_part = email.split("@")[0].lower()
    name_parts = re.split(r"[.\-_]", local_part)
    name_parts = [p for p in name_parts if p]
    # Strip characters that are not alphanumeric (e.g. '+' in 'doe+work',
    # '=' in 'user=tag') so that all generated candidates satisfy
    # is_safe_dir_segment().  RFC 5321/5322 email local-parts allow many
    # special characters that would otherwise produce an unsafe identity
    # segment and fall back to unscoped for affected users.
    name_parts = [re.sub(r"[^a-z0-9]", "", p) for p in name_parts]
    name_parts = [p for p in name_parts if p]

    if not name_parts:
        return "default"

    first = name_parts[0]
    second = name_parts[1] if len(name_parts) > 1 else first

    # Build initial candidate (3 chars when possible)
    if len(name_parts) == 1:
        candidate = first[:3]
    else:
        candidate = first[0] + second[:2]

    if not candidate:
        return "default"  # pragma: no cover – defensive; name_parts is non-empty

    # Build owner map from existing identity directories.
    # Directories *without* a ``.identity-owner`` file are treated as claimed
    # by an unknown agent (empty-string sentinel) to avoid cross-agent
    # collisions with pre-existing or manually-created directories.
    workflows_dir = git_root / ".agdt" / "workflows"
    owner_map: dict[str, str] = {}  # directory name -> email (or "" for unclaimed)
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

    # Collision resolution: try extending from second name / first name
    first_idx = 1  # chars consumed from first name (already used [0])
    second_idx = 2 if len(name_parts) > 1 else 3  # chars consumed from second name

    max_iters = len(first) + len(second) + 10  # safety bound
    for _ in range(max_iters):  # pragma: no branch
        opt_a: str | None = None
        opt_b: str | None = None

        # Option A: extend second name
        if second_idx < len(second):
            opt_a = first[:first_idx] + second[: second_idx + 1] if len(name_parts) > 1 else first[: second_idx + 1]
        # Option B: extend first name
        if first_idx < len(first) and len(name_parts) > 1:
            opt_b = first[: first_idx + 1] + second[:second_idx]

        # Evaluate which option is unique
        a_unique = opt_a is not None and not _is_collision(opt_a)
        b_unique = opt_b is not None and not _is_collision(opt_b)

        if a_unique and b_unique:
            # Both unique — pick shorter; prefer A (second name) on tie
            assert opt_a is not None and opt_b is not None
            if len(opt_a) <= len(opt_b):
                return opt_a
            return opt_b  # pragma: no cover – opt_a/opt_b same length at equal indices
        elif a_unique:
            assert opt_a is not None
            return opt_a
        elif b_unique:
            assert opt_b is not None
            return opt_b
        else:
            # Neither unique — advance both indices and keep trying
            if opt_a is not None:
                second_idx += 1
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


def get_bootstrap_state() -> dict[str, str]:
    """Read identity and worktree_key from their respective cache files.

    Identity is read from ``.agdt/identity.json`` (new); ``worktree_key``
    is read from ``.agdt/runtime-bootstrap.json``.  For installations that
    have not yet been migrated, identity falls back to the bootstrap file.

    Returns a dict with ``"identity"`` and/or ``"worktree_key"`` keys.
    Returns ``{}`` when no data is found or not in a git repo.

    This function must NOT call ``get_state_dir()`` or ``load_state()`` to
    avoid circular dependency.
    """
    git_root = _get_git_repo_root()
    if git_root is None:
        return {}

    agdt_dir = git_root / ".agdt"
    result: dict[str, str] = {}

    # Read identity from identity.json (new approach)
    identity_cache = _read_identity_cache(agdt_dir)
    if identity_cache is not None:
        result["identity"] = identity_cache["identity"]

    # Read worktree_key (and legacy identity) from bootstrap file
    bootstrap_path = agdt_dir / BOOTSTRAP_FILENAME
    try:
        content = bootstrap_path.read_text(encoding="utf-8")
        data = json.loads(content)
        if not isinstance(data, dict):
            return result
        # worktree_key always comes from bootstrap
        value = data.get("worktree_key")
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                result["worktree_key"] = stripped
        # Legacy fallback: read identity from bootstrap when identity.json is absent
        if "identity" not in result:
            legacy_id = data.get("identity")
            if isinstance(legacy_id, str):
                stripped = legacy_id.strip()
                if stripped:
                    result["identity"] = stripped
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError, OSError):
        pass

    return result


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


def is_safe_dir_segment(segment: str) -> bool:
    """Return True if ``segment`` is safe to use as a single directory name.

    A safe segment:

    - is non-empty after stripping
    - is not ``"."`` or ``".."``
    - does not contain path separators (``/`` or ``\\``) or ``":"``
    - does not contain ``".."`` anywhere inside the string
    - consists only of alphanumeric characters (including non-ASCII) plus
      ``._-+'``

    This is the **centralised** safety check used by ``get_state_dir()``,
    ``set_bootstrap_state()``, and ``_run_auto_execute_command()`` to prevent
    a tampered bootstrap or identity cache file from escaping
    ``.agdt/workflows/``.
    """
    segment = segment.strip()
    if not segment or segment in {".", ".."}:
        return False
    if "/" in segment or "\\" in segment or ":" in segment:
        return False
    if ".." in segment:
        return False
    # Allow Unicode alphanumerics plus a small set of safe punctuation that
    # commonly appears in email local-parts (used for identity scoping).
    allowed_punctuation = "._-+'"
    for ch in segment:
        if not (ch.isalnum() or ch in allowed_punctuation):
            return False
    return True


def _read_identity_cache(agdt_dir: Path) -> dict[str, str] | None:
    """Read the identity cache from ``.agdt/identity.json``.

    Returns a dict with ``"identity"`` and ``"email"`` keys when the file
    exists and contains valid data, or ``None`` when the file is missing,
    malformed, or does not satisfy all of:

    - ``"identity"`` is a non-empty, safe directory segment after stripping
      whitespace
    - ``"email"`` is present and is a string (may be empty)
    """
    cache_path = agdt_dir / IDENTITY_CACHE_FILENAME
    try:
        content = cache_path.read_text(encoding="utf-8")
        data = json.loads(content)
        if not isinstance(data, dict):
            return None
        identity = data.get("identity")
        email = data.get("email")
        if not (isinstance(identity, str) and isinstance(email, str)):
            return None
        identity_stripped = identity.strip()
        if not identity_stripped:
            return None

        if is_safe_dir_segment(identity_stripped):
            return {"identity": identity_stripped, "email": email}

        # Cached identity is present but fails the safety check; return None to
        # signal that the entry is unusable. Callers that perform identity
        # resolution (e.g. _get_or_refresh_identity) may choose to re-resolve
        # and rewrite the cache, while simpler callers like get_state_dir() /
        # get_bootstrap_state() will just fall back without modifying it.
        return None
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None


def _write_identity_cache(agdt_dir: Path, identity: str, email: str) -> None:
    """Write the identity cache to ``.agdt/identity.json``.

    Silent no-op on write errors.
    """
    try:
        agdt_dir.mkdir(parents=True, exist_ok=True)
        cache_path = agdt_dir / IDENTITY_CACHE_FILENAME
        cache_path.write_text(
            json.dumps({"identity": identity, "email": email}, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def _get_or_refresh_identity(git_root: Path, *, _email: str | None = None) -> str:
    """Get identity from cache (``.agdt/identity.json``) or resolve and cache it.

    Validates the cache by comparing the stored email with the current
    ``git config user.email``.  When they match (including when both are empty
    strings), returns the cached identity without calling ``_resolve_identity()``
    (avoids the filesystem collision scan under ``.agdt/workflows/``).  When
    they differ or the cache is absent, calls ``_resolve_identity()`` and writes
    the result to ``.agdt/identity.json``.

    On a cache miss, the resolved identity will be ``"default"`` when
    ``git config user.email`` is unavailable.

    *_email* is an optional keyword-only argument.  When provided it is used
    directly, skipping the ``git config user.email`` subprocess call.
    Callers that have already fetched the email (e.g. ``set_bootstrap_state``)
    should pass it here to eliminate redundant subprocess overhead.
    """
    agdt_dir = git_root / ".agdt"
    current_email = _email if _email is not None else _get_git_email()

    # Use cache when email has not changed
    cached = _read_identity_cache(agdt_dir)
    if cached is not None and cached["email"] == current_email:
        return cached["identity"]

    # Cache miss or stale — resolve and update cache.
    # Pass current_email to avoid a second `git config user.email` subprocess call.
    identity = _resolve_identity(git_root, _email=current_email)
    _write_identity_cache(agdt_dir, identity, current_email)
    return identity


def set_bootstrap_state(
    identity: str | None = None,
    worktree_key: str | None = None,
) -> None:
    """Write (or update) the bootstrap file and identity cache.

    Identity is stored in ``.agdt/identity.json`` (validated against
    ``git config user.email`` on every call; re-resolved only on mismatch).
    ``runtime-bootstrap.json`` stores only ``worktree_key``.

    If *identity* is ``None`` it is obtained via ``_get_or_refresh_identity()``.
    Existing ``worktree_key`` is preserved when *worktree_key* is not passed.
    Also writes ``.identity-owner`` under ``.agdt/workflows/{identity}/``.

    Silent no-op when not in a git repo.
    """
    git_root = _get_git_repo_root()
    if git_root is None:
        return

    # Fetch git email once — reused for identity cache, _get_or_refresh_identity,
    # and the .identity-owner file to avoid multiple subprocess calls.
    email = _get_git_email()

    # Normalize caller-provided identity: must be str, stripped, non-empty, and safe as
    # a single directory segment (no path separators, "..", colons, or non-printable chars).
    # Unsafe values are treated as unset and fall through to _get_or_refresh_identity().
    if identity is not None:
        if isinstance(identity, str):
            stripped = identity.strip()
            identity = stripped if stripped and is_safe_dir_segment(stripped) else None
        else:
            identity = None  # Non-str values treated as unset

    # Get identity via cache (email-based validation) or explicit value
    if identity is None:
        identity = _get_or_refresh_identity(git_root, _email=email)
    else:
        # Explicit identity provided — write it to cache (reuse pre-fetched email)
        _write_identity_cache(git_root / ".agdt", identity, email)

    # Ensure resolved identity is safe as a single directory segment. This defends against
    # unsafe values that might be returned from _get_or_refresh_identity() (e.g. email
    # local-parts containing path separators). Treat invalid/unsafe identity as absent so
    # that callers fall back to the true _unscoped path rather than using "_unscoped" as
    # a scoped identity name (which would route to .agdt/workflows/_unscoped/<worktree_key>
    # instead of the intended .agdt/workflows/_unscoped/).
    if not isinstance(identity, str) or not is_safe_dir_segment(identity):
        identity = ""

    # Read existing bootstrap to preserve worktree_key
    bootstrap_path = git_root / ".agdt" / BOOTSTRAP_FILENAME
    existing: dict[str, str] = {}
    try:
        content = bootstrap_path.read_text(encoding="utf-8")
        data = json.loads(content)
        if isinstance(data, dict):
            bv = data.get("worktree_key")
            if isinstance(bv, str):
                stripped = bv.strip()
                if stripped:
                    existing["worktree_key"] = stripped
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError, OSError):
        pass

    # Normalize caller-provided worktree_key: must be str, stripped, non-empty
    effective_wk: str | None = None
    if worktree_key is not None:
        if isinstance(worktree_key, str):
            stripped_wk = worktree_key.strip()
            if stripped_wk:
                effective_wk = stripped_wk
        # Non-str or whitespace-only worktree_key → treated as deletion

    if worktree_key is not None:
        if effective_wk is not None:
            existing["worktree_key"] = effective_wk
        else:
            existing.pop("worktree_key", None)

    # Write bootstrap file (worktree_key only; identity lives in identity.json)
    bootstrap_path.parent.mkdir(parents=True, exist_ok=True)
    bootstrap_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    # Ensure .agdt/.gitignore exists (silent — no user-facing message here)
    from agentic_devtools.agdt_gitignore import ensure_agdt_gitignore

    ensure_agdt_gitignore(git_root)

    # Write .identity-owner file (reuse email fetched at start of function)
    if identity:
        identity_dir = git_root / ".agdt" / "workflows" / identity
        identity_dir.mkdir(parents=True, exist_ok=True)
        owner_file = identity_dir / IDENTITY_OWNER_FILENAME
        if email:
            owner_file.write_text(email, encoding="utf-8")


# ---------------------------------------------------------------------------
# Pin file infrastructure (race condition fix #1180)
# ---------------------------------------------------------------------------


def write_pin_file(
    state_dir: str | Path,
    workflow: str,
    ttl_hours: int = DEFAULT_PIN_TTL_HOURS,
) -> Path | None:
    """Write the pin file atomically at ``.agdt/pinned-state-dir.json``.

    The pin file allows independent CLI invocations to resolve the same state
    directory that was determined at workflow initiation time, eliminating the
    race condition where ``runtime-bootstrap.json`` could be modified by a
    background task between reads.

    Args:
        state_dir: Absolute path to the resolved state directory.
        workflow: Workflow name (must be in ``RECOGNIZED_PIN_WORKFLOWS``).
        ttl_hours: Hours before the pin expires (default 24).

    Returns:
        Path to the written pin file, or ``None`` if not in a git repo.

    Raises:
        ValueError: If ``workflow`` is not in ``RECOGNIZED_PIN_WORKFLOWS``
            or ``ttl_hours`` is not a positive integer.
    """
    if workflow not in RECOGNIZED_PIN_WORKFLOWS:
        raise ValueError(f"workflow must be one of {sorted(RECOGNIZED_PIN_WORKFLOWS)}, got {workflow!r}")
    if not isinstance(ttl_hours, int) or isinstance(ttl_hours, bool) or ttl_hours <= 0:
        raise ValueError(f"ttl_hours must be a positive integer, got {ttl_hours!r}")

    git_root = _get_git_repo_root()
    if git_root is None:
        return None

    agdt_dir = git_root / ".agdt"
    agdt_dir.mkdir(parents=True, exist_ok=True)
    pin_path = agdt_dir / PIN_FILENAME

    resolved = Path(state_dir).resolve()
    payload = {
        "state_dir": str(resolved),
        "workflow": workflow,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "ttl_hours": ttl_hours,
    }

    # Atomic write: write to temp file then os.replace()
    fd, tmp_path = tempfile.mkstemp(dir=str(agdt_dir), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_path, str(pin_path))
    except BaseException:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return pin_path


def read_and_validate_pin_file(git_root: Path) -> Path | None:
    """Read and validate the pin file, returning the pinned state directory.

    Validation checks (any failure causes the pin to be ignored):
    1. File exists and is valid JSON.
    2. Required fields (``state_dir``, ``workflow``, ``created_utc``, ``ttl_hours``) present.
    3. ``workflow`` is in ``RECOGNIZED_PIN_WORKFLOWS``.
    4. ``state_dir`` is an absolute path.
    5. ``state_dir`` is inside ``.agdt/workflows/`` (directory traversal safety).
    6. TTL not expired (``created_utc`` + ``ttl_hours`` > now).
    7. ``state_dir`` exists or can be created.

    Args:
        git_root: Path to the git repository root.

    Returns:
        Validated ``Path`` to the state directory, or ``None`` if invalid/absent.
    """
    pin_path = git_root / ".agdt" / PIN_FILENAME

    try:
        if not pin_path.is_file():
            return None
        raw = pin_path.read_text(encoding="utf-8")
    except OSError:
        return None

    # Parse JSON
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        _emit_pin_diagnostic("Pin file is not valid JSON, ignoring")
        return None

    if not isinstance(data, dict):
        _emit_pin_diagnostic("Pin file content is not a JSON object, ignoring")
        return None

    # Required fields
    state_dir_str = data.get("state_dir")
    workflow = data.get("workflow")
    created_utc = data.get("created_utc")
    ttl_hours = data.get("ttl_hours")

    if state_dir_str is None or workflow is None or created_utc is None or ttl_hours is None:
        _emit_pin_diagnostic("Pin file missing required fields, ignoring")
        return None

    if not state_dir_str or not workflow or not created_utc:
        _emit_pin_diagnostic("Pin file has empty required string fields, ignoring")
        return None

    # ttl_hours must be a positive number
    if not isinstance(ttl_hours, (int, float)) or isinstance(ttl_hours, bool) or ttl_hours <= 0:
        _emit_pin_diagnostic(f"Pin file has invalid ttl_hours ({ttl_hours!r}), ignoring")
        return None

    # Workflow must be recognized
    if workflow not in RECOGNIZED_PIN_WORKFLOWS:
        _emit_pin_diagnostic(f"Pin file workflow '{workflow}' not recognized, ignoring")
        return None

    # state_dir must be absolute
    state_dir_path = Path(state_dir_str)
    if not state_dir_path.is_absolute():
        _emit_pin_diagnostic("Pin file state_dir is not absolute, ignoring")
        return None

    # state_dir must be inside .agdt/workflows/ (directory traversal check)
    try:
        resolved_state = state_dir_path.resolve()
        resolved_root = git_root.resolve()
        workflows_root = resolved_root / ".agdt" / "workflows"
        resolved_state.relative_to(workflows_root)
    except (ValueError, OSError):
        _emit_pin_diagnostic("Pin file state_dir is outside .agdt/workflows/, ignoring")
        return None

    # TTL check
    try:
        created = datetime.fromisoformat(created_utc)
        # Ensure timezone-aware comparison
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        elapsed_hours = (now - created).total_seconds() / 3600
        if elapsed_hours > ttl_hours:
            _emit_pin_diagnostic(
                f"Pin file expired (created {created_utc}, TTL {ttl_hours}h), falling back to bootstrap"
            )
            return None
    except (ValueError, TypeError, OverflowError):
        _emit_pin_diagnostic("Pin file has invalid created_utc timestamp, ignoring")
        return None

    # state_dir must exist or be creatable — use the resolved path consistently
    try:
        resolved_state.mkdir(parents=True, exist_ok=True)
    except OSError:
        _emit_pin_diagnostic(f"Pin file state_dir '{state_dir_str}' does not exist and cannot be created, ignoring")
        return None

    return resolved_state


def delete_pin_file(git_root: Path | None = None) -> None:
    """Delete the pin file if it exists. Silent no-op if absent.

    Args:
        git_root: Path to the git repository root. If None, auto-detected.
    """
    if git_root is None:
        git_root = _get_git_repo_root()
    if git_root is None:
        return

    pin_path = git_root / ".agdt" / PIN_FILENAME
    try:
        pin_path.unlink(missing_ok=True)
    except OSError:
        pass


def refresh_pin_file_ttl() -> None:
    """Refresh the pin file's ``created_utc`` to prevent TTL expiration.

    Reads the existing pin, validates it minimally (must be valid JSON with
    required fields), then atomically rewrites with updated ``created_utc``.
    No-op if pin file is absent, invalid, or not in a git repo.
    """
    git_root = _get_git_repo_root()
    if git_root is None:
        return

    pin_path = git_root / ".agdt" / PIN_FILENAME
    try:
        if not pin_path.is_file():
            return
        raw = pin_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError, ValueError):
        return

    if not isinstance(data, dict):
        return

    # Must have minimum required fields to be worth refreshing
    if not all(data.get(k) for k in ("state_dir", "workflow", "created_utc", "ttl_hours")):
        return

    # Validate fields match what read_and_validate_pin_file() would accept
    workflow = data["workflow"]
    ttl_hours = data["ttl_hours"]
    state_dir_str = data["state_dir"]

    if workflow not in RECOGNIZED_PIN_WORKFLOWS:
        return

    if not isinstance(ttl_hours, (int, float)) or isinstance(ttl_hours, bool) or ttl_hours <= 0:
        return

    state_dir_path = Path(state_dir_str)
    if not state_dir_path.is_absolute():
        return

    # Directory traversal check — must be under .agdt/workflows/
    try:
        resolved_state = state_dir_path.resolve()
        resolved_root = git_root.resolve()
        workflows_root = resolved_root / ".agdt" / "workflows"
        resolved_state.relative_to(workflows_root)
    except (ValueError, OSError):
        return

    # Update created_utc
    data["created_utc"] = datetime.now(timezone.utc).isoformat()

    # Atomic write
    agdt_dir = git_root / ".agdt"
    fd, tmp_path = tempfile.mkstemp(dir=str(agdt_dir), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, str(pin_path))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _emit_pin_diagnostic(message: str) -> None:
    """Emit a diagnostic message about pin file resolution to stderr.

    Uses a module-level flag to emit only once per process, avoiding spam
    when get_state_dir() is called multiple times.
    """
    global _pin_logged  # noqa: PLW0603
    if not _pin_logged:
        print(f"[agdt] {message}", file=sys.stderr)
        _pin_logged = True


def get_state_dir() -> Path:
    """Get the directory for storing the state file.

    Priority:
    1. ``AGENTIC_DEVTOOLS_STATE_DIR`` environment variable
    2. ``.agdt/pinned-state-dir.json`` — validated pin file (race condition fix)
    3. ``.agdt/workflows/{identity}/{worktree_key}/`` relative to git root.
       Identity is read from ``.agdt/identity.json``; worktree_key from
       ``.agdt/runtime-bootstrap.json``.  Legacy installations that have not
       yet created ``identity.json`` fall back to reading identity from the
       bootstrap file.
    4. ``.agdt/workflows/_unscoped/`` relative to git root (when identity or
       worktree_key is missing or incomplete)
    5. ``.agdt-temp/`` in CWD (when not in a git repo)
    """
    # 1. Environment variable override
    env_dir = os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR", "").strip()
    if env_dir:
        path = Path(env_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    # 2. Pin file resolution (race condition fix #1180)
    git_root = _get_git_repo_root()
    if git_root:
        pinned = read_and_validate_pin_file(git_root)
        if pinned is not None:
            return pinned

    # 3/4. Git-based resolution
    if git_root:
        agdt_dir = git_root / ".agdt"

        # Read identity from identity.json first (new); fall back to bootstrap (legacy)
        identity = ""
        identity_cache = _read_identity_cache(agdt_dir)
        if identity_cache is not None:
            identity = identity_cache["identity"]

        # Read worktree_key (and legacy identity) from bootstrap file
        bootstrap_path = agdt_dir / BOOTSTRAP_FILENAME
        bootstrap: dict[str, Any] = {}
        try:
            if bootstrap_path.is_file():
                bootstrap = json.loads(bootstrap_path.read_text(encoding="utf-8"))
                if not isinstance(bootstrap, dict):
                    bootstrap = {}
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            bootstrap = {}

        # Legacy fallback: read identity from bootstrap when identity.json absent
        if not identity:
            raw_id = bootstrap.get("identity", "")
            identity = raw_id.strip() if isinstance(raw_id, str) else ""

        raw_wk = bootstrap.get("worktree_key", "")
        worktree_key = raw_wk.strip() if isinstance(raw_wk, str) else ""

        if identity and worktree_key and is_safe_dir_segment(identity) and is_safe_dir_segment(worktree_key):
            scoped = git_root / ".agdt" / "workflows" / identity / worktree_key
            scoped.mkdir(parents=True, exist_ok=True)
            return scoped

        unscoped = git_root / ".agdt" / "workflows" / "_unscoped"
        unscoped.mkdir(parents=True, exist_ok=True)
        return unscoped

    # 5. Final fallback — not in a git repo
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
    ``AGENTIC_DEVTOOLS_STATE_DIR`` (when set) or the current working
    directory, looking for a ``.agdt`` directory.

    If the bootstrap file does not exist but the ``.agdt/`` directory does,
    the file is created with just ``{"worktree_key": ...}``.  Identity is
    read from ``.agdt/identity.json`` by ``get_state_dir()`` independently,
    so the scoped state path resolves correctly as soon as ``identity.json``
    is present — no ``set_bootstrap_state()`` call required.

    This exists so that ``set_value()`` and ``set_context_value()`` can keep
    the bootstrap in sync without interfering with tests that globally mock
    ``subprocess.run``.
    """
    try:
        # Choose a subprocess-free starting point (same priority as
        # get_state_dir()'s env-var check):
        # 1. AGENTIC_DEVTOOLS_STATE_DIR
        # 2. Current working directory as a reasonable default inside the repo
        env_dir = os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR", "").strip()
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


def load_state(use_locking: bool = False, lock_timeout: float = DEFAULT_LOCK_TIMEOUT) -> dict[str, Any]:
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
    state: dict[str, Any],
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


def load_state_locked(lock_timeout: float = DEFAULT_LOCK_TIMEOUT) -> dict[str, Any]:
    """
    Load state with file locking enabled.

    Convenience function for operations that need concurrent access safety.

    Args:
        lock_timeout: Maximum time to wait for lock in seconds

    Returns:
        Dictionary of all state values
    """
    return load_state(use_locking=True, lock_timeout=lock_timeout)


def save_state_locked(state: dict[str, Any], lock_timeout: float = DEFAULT_LOCK_TIMEOUT) -> Path:
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


@contextlib.contextmanager
def read_modify_write_state(
    lock_timeout: float = DEFAULT_LOCK_TIMEOUT,
) -> Iterator[dict[str, Any]]:
    """Load, mutate, and save state under an exclusive lock.

    Holds an exclusive lock across the entire load → mutate → save cycle
    so that concurrent processes cannot interleave reads and writes.

    Usage::

        with read_modify_write_state() as state:
            state["key"] = "value"

    If the caller raises an exception inside the context, the save is
    skipped and the exception propagates.  The lock is always released.

    Args:
        lock_timeout: Maximum time to wait for lock in seconds.

    Yields:
        The loaded state dictionary for in-place mutation.

    Raises:
        FileLockError: If the exclusive lock cannot be acquired.
    """
    state_dir = get_state_dir()
    path = state_dir / STATE_FILENAME

    wrote = False
    with locked_state_file(path, timeout=lock_timeout) as f:
        content = f.read()
        try:
            loaded = json.loads(content) if content.strip() else {}
        except json.JSONDecodeError:
            loaded = {}
        state: dict[str, Any] = loaded if isinstance(loaded, dict) else {}
        original_content = json.dumps(state, indent=2, ensure_ascii=False)
        yield state

        # Save in-place (still under the exclusive lock)
        new_content = json.dumps(state, indent=2, ensure_ascii=False)
        if new_content != original_content:
            f.seek(0)
            f.write(new_content)
            f.truncate()
            f.flush()
            os.fsync(f.fileno())
            wrote = True

    if wrote:
        # Signal that workflow state has been mutated. The CLI runner calls
        # persist_if_dirty() after every command to commit pending changes to
        # the -agdt branch automatically.
        try:
            from .cli.git.agdt_branch import mark_dirty

            mark_dirty()
        except ImportError:  # pragma: no cover
            pass  # agdt_branch not available (e.g., minimal install)


def get_value(key: str, required: bool = False) -> Any | None:
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
    _sync_bootstrap_for_context_key(key, value, state)


def _sync_bootstrap_for_context_key(key: str, value: Any, state: dict[str, Any]) -> None:
    """Sync ``runtime-bootstrap.json`` after a context-switching key changes.

    Uses ``_update_bootstrap_worktree_key`` (subprocess-free) to avoid
    consuming mock ``side_effect``s in tests that globally patch
    ``subprocess.run``.

    Called from both ``set_value()`` and ``set_context_value()`` to ensure
    the bootstrap worktree_key stays up-to-date regardless of entry path.

    Args:
        key: The context-switching key that was just written.
        value: The value that was written.
        state: The *current* in-memory state dict (already saved to disk).
    """
    try:
        if key == "issue_key":
            # Top-level issue_key — provider-agnostic identifier.
            # Accept both strings ("PROJECT-1234", "#42") and plain ints (42)
            # because agdt-set JSON-parses numeric values to int.
            # Reject complex types (dict/list/bool) to avoid writing
            # unintended values into the bootstrap file.
            if type(value) is int:  # noqa: E721 – exclude bool (bool is subclass of int)
                _update_bootstrap_worktree_key(str(value))
            elif isinstance(value, str):
                issue_key = value.strip()
                if issue_key:
                    _update_bootstrap_worktree_key(issue_key)
        elif key == "jira.issue_key":
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
            pr_id_str: str | None = None
            if type(value) is int:  # noqa: E721
                pr_id_str = str(value)
            elif isinstance(value, str):
                candidate = value.strip()
                if candidate.isdigit():
                    pr_id_str = candidate
            if pr_id_str:
                # Skip the bootstrap update when issue_key or jira.issue_key is
                # already set — the issue key has higher priority as worktree_key
                # (matching resolve_worktree_key() priority in agdt_branch.py).
                # This prevents set_value("pull_request_id", ...) from overwriting
                # the issue-key scope after an issue key has already set it.
                # Normalize issue_key: accept str and plain int (agdt-set
                # JSON-parses "42" to int), reject complex types (dict/list/bool).
                raw_issue_key = state.get("issue_key", "")
                if type(raw_issue_key) is int:  # noqa: E721 – exclude bool
                    top_level_issue_key = str(raw_issue_key)
                elif isinstance(raw_issue_key, str):
                    top_level_issue_key = raw_issue_key.strip()
                else:
                    top_level_issue_key = ""
                jira_val = state.get("jira")
                existing_jira_key = jira_val.get("issue_key", "") if isinstance(jira_val, dict) else ""
                has_issue_key = bool(top_level_issue_key) or (
                    isinstance(existing_jira_key, str) and bool(existing_jira_key.strip())
                )
                if not has_issue_key:
                    _update_bootstrap_worktree_key(f"PR{pr_id_str}")
    except Exception:  # noqa: BLE001 – bootstrap failure is non-fatal
        pass


# Context-switching keys that may trigger cross-lookup
CONTEXT_SWITCH_KEYS = {"pull_request_id", "jira.issue_key", "issue_key"}


def set_context_value(
    key: str,
    value: Any,
    trigger_cross_lookup: bool = True,
    verbose: bool = True,
) -> bool:
    """
    Set a context-switching value (pull_request_id, jira.issue_key, or issue_key).

    When one of these primary context keys changes to a NEW value:
    1. Atomically updates the value and deletes the counterpart key(s) in a
       single load/save cycle to prevent stale data
    2. Optionally triggers a background cross-lookup for the related key

    Counterpart logic:
    - pull_request_id -> clears both issue_key and jira.issue_key
    - issue_key -> clears pull_request_id (does NOT clear jira.issue_key)
    - jira.issue_key -> clears pull_request_id (does NOT clear issue_key)

    Cross-lookup behavior:
    - pull_request_id change -> looks up jira.issue_key from PR source branch/title
    - jira.issue_key change -> looks up pull_request_id from Jira/Azure DevOps
    - issue_key change -> no cross-lookup (provider-agnostic)

    Args:
        key: Must be "pull_request_id", "jira.issue_key", or "issue_key"
        value: The new value to set
        trigger_cross_lookup: If True, start background task to find related key
        verbose: If True, print status messages

    Returns:
        True if the value changed, False if unchanged

    Raises:
        ValueError: If key is not a context-switching key, or if
            ``key == "issue_key"`` and value is not a non-empty string
            (after stripping whitespace) or a plain ``int`` (excluding
            ``bool`` and ``int`` subclasses).
    """
    if key not in CONTEXT_SWITCH_KEYS:
        raise ValueError(f"set_context_value only accepts: {CONTEXT_SWITCH_KEYS}")

    # Validate issue_key type before clearing counterparts — accept only
    # non-empty str or plain int (excluding bool, a subclass of int).
    # Uses ``type(value) is int`` (not ``isinstance``) to match the read
    # and resolve paths (_get_issue_key_from_state, resolve_worktree_key)
    # and bootstrap sync, which all use the same strict check to exclude
    # bool and int subclasses.
    # This prevents ``agdt-set issue_key true`` (JSON-parsed to bool) or
    # complex types (dict/list) from wiping pull_request_id and leaving
    # no resolvable worktree key.
    if key == "issue_key":
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("issue_key must be a non-empty string (after stripping whitespace)")
        elif type(value) is not int:  # noqa: E721 – exclude bool and int subclasses
            raise ValueError(
                f"issue_key must be a non-empty string or plain integer, got {type(value).__name__}: {value!r}"
            )

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

    # Determine counterparts to clear:
    # - pull_request_id clears both issue_key and jira.issue_key
    # - issue_key or jira.issue_key only clears pull_request_id
    #   (both represent issue context; neither clears the other for
    #   backward compatibility — they may coexist with different values)
    if key == "pull_request_id":
        counterparts = ["jira.issue_key", "issue_key"]
    else:
        counterparts = ["pull_request_id"]

    # Atomic update: set the new key and clear the stale counterpart(s) in a
    # single load/save cycle to prevent a transient on-disk state where both
    # context keys exist (which could cause incorrect worktree key resolution
    # since issue_key/jira.issue_key has higher priority than pull_request_id
    # in resolve_worktree_key).  Cross-lookup will repopulate the counterpart.
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

    # Delete counterparts (supports dot notation for jira.issue_key)
    for counterpart in counterparts:
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

    # Keep bootstrap in sync — counterparts have already been cleared in
    # ``state``, so the priority check inside the helper sees the correct
    # post-clear picture (e.g., pull_request_id won't be skipped due to a
    # stale issue_key that was just deleted).
    _sync_bootstrap_for_context_key(key, value, state)

    # Trigger cross-lookup in background only for supported context keys.
    # This keeps the behavior aligned with ``_trigger_cross_lookup()``'s
    # documented contract and avoids relying on it to silently no-op for
    # unrelated keys such as ``issue_key``.
    if trigger_cross_lookup and key in {"pull_request_id", "jira.issue_key"}:
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

    Extracts issue key from PR source branch name (e.g., feature/PROJECT-1234/...).
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


def get_all_keys() -> list[str]:
    """Get list of all keys in state."""
    return list(load_state().keys())


# Convenience functions for common parameters


if TYPE_CHECKING:

    @overload
    def get_pull_request_id(required: Literal[True]) -> int: ...

    @overload
    def get_pull_request_id(required: bool = ...) -> int | None: ...


def get_pull_request_id(required: bool = False) -> int | None:
    """Get the pull request ID from state."""
    value = get_value("pull_request_id", required=required)
    return int(value) if value is not None else None


def set_pull_request_id(pull_request_id: int) -> None:
    """Set the pull request ID in state."""
    set_value("pull_request_id", pull_request_id)


if TYPE_CHECKING:

    @overload
    def get_thread_id(required: Literal[True]) -> int: ...

    @overload
    def get_thread_id(required: bool = ...) -> int | None: ...


def get_thread_id(required: bool = False) -> int | None:
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


def get_pypi_package_name(required: bool = False) -> str | None:
    """Get the PyPI package name from state."""
    value = get_value("pypi.package_name", required=required)
    return str(value) if value is not None else None


def set_pypi_package_name(package_name: str) -> None:
    """Set the PyPI package name in state."""
    set_value("pypi.package_name", package_name)


def get_pypi_version(required: bool = False) -> str | None:
    """Get the PyPI version from state."""
    value = get_value("pypi.version", required=required)
    return str(value) if value is not None else None


def set_pypi_version(version: str) -> None:
    """Set the PyPI version in state."""
    set_value("pypi.version", version)


def get_pypi_repository(required: bool = False) -> str | None:
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


def get_workflow_state() -> dict[str, Any] | None:
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
    step: str | None = None,
    context: dict[str, Any] | None = None,
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

    workflow_data: dict[str, Any] = {
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


def clear_workflow_state(force_delete: bool = False, completing_workflow: str | None = None) -> None:
    """Clear the workflow state (end the current workflow).

    Args:
        force_delete: When True (used by ``agdt-clear-workflow``), unconditionally
            delete the pin file regardless of its ``workflow`` field.
        completing_workflow: When provided (used by workflow-completion handlers),
            delete the pin file only if its ``workflow`` field matches this value.
    """
    delete_value("workflow")

    # Pin file cleanup
    git_root = _get_git_repo_root()
    if git_root is None:
        return

    if force_delete:
        # Unconditional delete (agdt-clear-workflow)
        delete_pin_file(git_root)
    elif completing_workflow:
        # Conditional delete: only if pin workflow matches the completing workflow
        pin_path = git_root / ".agdt" / PIN_FILENAME
        try:
            if pin_path.is_file():
                data = json.loads(pin_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("workflow") == completing_workflow:
                    delete_pin_file(git_root)
        except (OSError, json.JSONDecodeError, ValueError):
            pass


def is_workflow_active(workflow_name: str | None = None) -> bool:
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


def update_workflow_step(step: str, status: str | None = None) -> None:
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


def update_workflow_context(context: dict[str, Any]) -> None:
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
