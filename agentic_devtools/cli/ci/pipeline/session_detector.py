"""Copilot session activity detector.

Replaces the squash-wait state machine with a simple check of the
Issues Events API.
"""

from __future__ import annotations

import logging

from agentic_devtools.cli.ci.models import (
    COPILOT_SESSION_EVENT_FINISHED,
    COPILOT_SESSION_EVENT_FINISHED_FAILURE,
    COPILOT_SESSION_EVENT_STARTED,
)
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)


def is_copilot_session_active(provider: CIPlatformProvider, pr_number: int) -> bool:
    """Check if a Copilot coding session is currently active.

    Looks for the latest copilot_work_started event and checks whether
    a terminal event (finished or failure) exists with a higher ID.

    This single check replaces the entire squash-wait state machine for
    actions 4 (resolve threads), 5 (dispatch repair), and 6 (squash).

    Args:
        provider: CI platform provider.
        pr_number: Pull request number.

    Returns:
        True if an active Copilot session is detected or if the events API
        is unavailable (fail-closed to prevent unsafe side effects).
        False only when a terminal event is confirmed after the latest start.
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

    latest_start = None
    for event in events:
        if event.event == COPILOT_SESSION_EVENT_STARTED:
            if latest_start is None or event.id > latest_start.id:
                latest_start = event

    if latest_start is None:
        logger.info("PR #%d: No copilot_work_started events found", pr_number)
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

    logger.info(
        "PR #%d: Active Copilot session detected (started id=%d, no terminal event)",
        pr_number,
        latest_start.id,
    )
    return True
