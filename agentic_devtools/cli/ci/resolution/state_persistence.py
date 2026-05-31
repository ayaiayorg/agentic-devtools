"""State persistence for tentative thread resolutions.

Handles serialization/deserialization of ThreadResolutionState, TTL
calculation, and expiry detection for tentative resolution re-evaluation.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, ThreadResolutionState

logger = logging.getLogger(__name__)


def _thread_id_to_filename(thread_id: str) -> str:
    """Encode a thread ID as a URL-safe base64 filename stem.

    Uses URL-safe base64 (RFC 4648 §5) so the mapping is injective:
    distinct thread IDs always produce distinct filenames regardless of
    the characters they contain (e.g. ``a/b`` and ``a_b`` map to
    different encodings).
    """
    return base64.urlsafe_b64encode(thread_id.encode()).decode()


def save_resolution_state(state: ThreadResolutionState, state_dir: Path) -> None:
    """Persist a thread's resolution state to disk.

    Args:
        state: The thread resolution state to save.
        state_dir: Directory to store state files.
    """
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        safe_id = _thread_id_to_filename(state.thread_id)
        file_path = state_dir / f"{safe_id}.json"
        file_path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
    except OSError as exc:
        logger.error("Failed to save resolution state for %s: %s", state.thread_id, exc)


def load_resolution_state(thread_id: str, state_dir: Path) -> ThreadResolutionState | None:
    """Load a thread's resolution state from disk.

    Args:
        thread_id: The thread identifier.
        state_dir: Directory containing state files.

    Returns:
        ThreadResolutionState if found, None otherwise.
    """
    safe_id = _thread_id_to_filename(thread_id)
    file_path = state_dir / f"{safe_id}.json"

    if not file_path.exists():
        return None

    try:
        data = json.loads(file_path.read_text())
        return ThreadResolutionState.from_dict(data)
    except (json.JSONDecodeError, KeyError, OSError, TypeError, ValueError) as exc:
        logger.warning("Failed to load resolution state for %s: %s", thread_id, exc)
        return None


def is_tentative_expired(state: ThreadResolutionState) -> bool:
    """Check whether a tentative resolution has expired.

    Args:
        state: The thread resolution state.

    Returns:
        True if the tentative has exceeded its TTL (5 iterations or 24h).
    """
    return state.is_expired()


def increment_iteration(state: ThreadResolutionState, state_dir: Path) -> ThreadResolutionState:
    """Increment iteration count and persist updated state.

    Args:
        state: The current state.
        state_dir: Directory containing state files.

    Returns:
        The updated state.
    """
    state.increment_iteration()
    save_resolution_state(state, state_dir)
    return state


def mark_abandoned(thread_id: str, state_dir: Path) -> None:
    """Persist an ABANDONED verdict for a thread that has exceeded its TTL.

    Overwrites the existing state with ``ResolutionVerdict.ABANDONED`` so
    that subsequent finalization passes detect the permanent abandonment and
    skip re-entering the tentative lifecycle.

    If no state file exists for *thread_id* the function is a no-op, because
    a thread that never entered the tentative lifecycle has nothing to abandon.

    Args:
        thread_id: The thread identifier.
        state_dir: Directory containing state files.
    """
    existing = load_resolution_state(thread_id, state_dir)
    if existing is None:
        return
    existing.verdict = ResolutionVerdict.ABANDONED
    save_resolution_state(existing, state_dir)


def clear_resolution_state(thread_id: str, state_dir: Path) -> None:
    """Remove the resolution state file for a thread.

    Use this when a thread reaches a definitive (non-tentative) verdict so
    that any lingering tentative state is cleaned up.  Unlike
    :func:`mark_abandoned`, this does *not* leave behind an ABANDONED marker,
    allowing the thread to re-enter the tentative lifecycle if the evaluation
    returns ``TENTATIVE`` in a future iteration.

    Args:
        thread_id: The thread identifier.
        state_dir: Directory containing state files.
    """
    safe_id = _thread_id_to_filename(thread_id)
    file_path = state_dir / f"{safe_id}.json"

    try:
        if file_path.exists():
            file_path.unlink()
    except OSError as exc:
        logger.warning("Failed to remove state for thread %s: %s", thread_id, exc)
