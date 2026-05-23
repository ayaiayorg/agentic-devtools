"""Evaluator lock mechanism.

Provides concurrency control for the post-agent evaluator using a single
PR comment as a distributed lock. The lock comment uses a marker to enable
find/update semantics via the provider's ``find_comment``/``update_comment``.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from ..provider import CIPlatformProvider

_LOCK_MARKER = "<!-- copilot-evaluator-lock -->"
_LOCK_TTL_SECONDS = 300  # 5-minute TTL for stale lock detection


def _get_writer_token() -> str:
    """Get a unique token for this evaluator run.

    Uses GITHUB_RUN_ID/GITHUB_RUN_ATTEMPT when in CI, falls back to
    a timestamp-based token for local development.
    """
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    if run_id and run_attempt:
        return f"{run_id}-{run_attempt}"
    return f"local-{int(time.time())}"


def _build_lock_body(token: str) -> str:
    """Build the lock comment body."""
    return f"{_LOCK_MARKER}\ntoken={token}\nacquired={time.time():.0f}\nstate=active"


def _parse_lock_body(body: str) -> tuple[str, float, str]:
    """Parse a lock comment body into (token, acquired_timestamp, state)."""
    token = ""
    acquired = 0.0
    state = ""
    for line in body.splitlines():
        if line.startswith("token="):
            token = line[6:]
        elif line.startswith("acquired="):
            try:
                acquired = float(line[9:])
            except ValueError:
                pass
        elif line.startswith("state="):
            state = line[6:]
    return token, acquired, state


@dataclass(frozen=True)
class LockStatus:
    """Current lock status.

    Attributes:
        is_locked: Whether the lock is currently held.
        holder: Token of the lock holder (empty if unlocked).
        age_seconds: Age of the lock in seconds (0 if unlocked).
        is_stale: Whether the lock has exceeded the TTL.
    """

    is_locked: bool = False
    holder: str = ""
    age_seconds: float = 0.0
    is_stale: bool = False


def check_lock_status(provider: CIPlatformProvider, pr_number: int) -> LockStatus:
    """Check the current lock status for a PR.

    Args:
        provider: CI platform provider.
        pr_number: Pull request number.

    Returns:
        LockStatus with current lock information.
    """
    result = provider.find_comment(pr_number, _LOCK_MARKER)
    if result is None:
        return LockStatus()

    _comment_id, body = result
    token, acquired, state = _parse_lock_body(body)

    if state != "active":
        return LockStatus()

    age = time.time() - acquired if acquired > 0 else 0.0
    is_stale = age > _LOCK_TTL_SECONDS

    return LockStatus(
        is_locked=True,
        holder=token,
        age_seconds=age,
        is_stale=is_stale,
    )


def acquire_lock(provider: CIPlatformProvider, pr_number: int) -> str | None:
    """Attempt to acquire the evaluator lock for a PR.

    If the lock is already held by another run and not stale, returns None.
    If the lock is stale, it is forcibly acquired.

    Args:
        provider: CI platform provider.
        pr_number: Pull request number.

    Returns:
        The lock token if acquired, None if lock is held by another run.
    """
    token = _get_writer_token()
    result = provider.find_comment(pr_number, _LOCK_MARKER)

    if result is not None:
        comment_id, body = result
        existing_token, acquired, state = _parse_lock_body(body)

        if state == "active":
            age = time.time() - acquired if acquired > 0 else float("inf")
            if age <= _LOCK_TTL_SECONDS and existing_token != token:
                # Lock held by another run, not stale
                return None
            # Stale lock or same token — take over

        # Update existing lock comment
        provider.update_comment(comment_id, _build_lock_body(token))
    else:
        # Create new lock comment
        provider.post_comment(pr_number, _build_lock_body(token))

    # Re-read canonical lock comment to verify ownership and avoid races where
    # multiple runs create/update lock comments concurrently.
    verification = provider.find_comment(pr_number, _LOCK_MARKER)
    if verification is None:
        return None

    _comment_id, verification_body = verification
    verified_token, _verified_acquired, verified_state = _parse_lock_body(verification_body)
    if verified_state != "active" or verified_token != token:
        return None

    return token


def release_lock(provider: CIPlatformProvider, pr_number: int, token: str) -> None:
    """Release the evaluator lock for a PR.

    Only releases if the current holder matches the provided token.

    Args:
        provider: CI platform provider.
        pr_number: Pull request number.
        token: Token of the lock holder requesting release.
    """
    result = provider.find_comment(pr_number, _LOCK_MARKER)
    if result is None:
        return

    comment_id, body = result
    existing_token, _, state = _parse_lock_body(body)

    if state == "active" and existing_token == token:
        released_body = f"{_LOCK_MARKER}\ntoken={token}\nacquired=0\nstate=released"
        provider.update_comment(comment_id, released_body)
