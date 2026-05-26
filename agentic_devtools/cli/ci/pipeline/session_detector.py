"""Copilot session activity detector.

Replaces the squash-wait state machine with a simple check of the
Issues Events API.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from agentic_devtools.cli.ci.models import (
    COPILOT_SESSION_EVENT_FINISHED,
    COPILOT_SESSION_EVENT_FINISHED_FAILURE,
    COPILOT_SESSION_EVENT_STARTED,
)
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)

_DEFAULT_MAX_SESSION_AGE_SECONDS = 3600  # 1 hour


def _get_max_session_age_seconds() -> int:
    """Return the max session age from environment or the default (3600s)."""
    raw = os.environ.get("AGDT_MAX_SESSION_AGE_SECONDS", "").strip()
    if raw:
        try:
            return int(raw)
        except ValueError:
            logger.warning(
                "AGDT_MAX_SESSION_AGE_SECONDS=%r is not a valid integer; using default %d",
                raw,
                _DEFAULT_MAX_SESSION_AGE_SECONDS,
            )
    return _DEFAULT_MAX_SESSION_AGE_SECONDS


def _is_session_stale(created_at: str, max_age_seconds: int) -> bool:
    """Return True if the session start event is older than max_age_seconds."""
    try:
        started_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        # If we cannot parse the timestamp, we cannot determine staleness —
        # fall back to treating as potentially active (conservative).
        return False
    age = (datetime.now(tz=timezone.utc) - started_time).total_seconds()
    return age > max_age_seconds


def is_copilot_session_active(provider: CIPlatformProvider, pr_number: int) -> bool:
    """Check if a Copilot coding session is currently active.

    Looks for the latest copilot_work_started event and checks whether
    a terminal event (finished or failure) exists with a higher ID.
    Additionally applies a staleness timeout: if the latest start event
    is older than ``AGDT_MAX_SESSION_AGE_SECONDS`` (default 3600s) with
    no terminal event, the session is considered stale/inactive.

    This single check replaces the entire squash-wait state machine for
    actions 4 (resolve threads), 5 (dispatch repair), and 6 (squash).

    Args:
        provider: CI platform provider.
        pr_number: Pull request number.

    Returns:
        True if an active Copilot session is detected or if the events API
        is unavailable (fail-closed to prevent unsafe side effects).
        False when a terminal event is confirmed after the latest start,
        or when the latest start event exceeds the staleness threshold.
    """
    try:
        events = provider.list_pr_issue_events(pr_number)
    except Exception as exc:
        logger.warning(
            "PR #%d: Failed to list issue events — assuming active session (fail-closed): %s",
            pr_number,
            exc,
        )
        return True

    logger.debug(
        "PR #%d: Fetched %d Copilot session event(s): %s",
        pr_number,
        len(events),
        [(e.id, e.event, e.created_at) for e in events],
    )

    latest_start = None
    for event in events:
        if event.event == COPILOT_SESSION_EVENT_STARTED:
            if latest_start is None or event.id > latest_start.id:
                latest_start = event

    if latest_start is None:
        logger.info("PR #%d: No copilot_work_started events found — not active", pr_number)
        return False

    has_terminal = any(
        e.id > latest_start.id
        for e in events
        if e.event in (COPILOT_SESSION_EVENT_FINISHED, COPILOT_SESSION_EVENT_FINISHED_FAILURE)
    )

    if has_terminal:
        logger.info(
            "PR #%d: Latest session (started id=%d) has terminal event — not active",
            pr_number,
            latest_start.id,
        )
        return False

    # Check staleness: if the start event is older than the threshold,
    # treat the session as inactive (handles cancelled/crashed sessions
    # that never emit a terminal event).
    max_age = _get_max_session_age_seconds()
    if _is_session_stale(latest_start.created_at, max_age):
        logger.info(
            "PR #%d: Session (started id=%d, created_at=%s) exceeds staleness threshold "
            "(%d seconds) — treating as inactive",
            pr_number,
            latest_start.id,
            latest_start.created_at,
            max_age,
        )
        return False

    logger.info(
        "PR #%d: Active Copilot session detected (started id=%d, created_at=%s, no terminal event)",
        pr_number,
        latest_start.id,
        latest_start.created_at,
    )
    return True
