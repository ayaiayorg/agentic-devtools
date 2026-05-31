"""Session merger for agent session tracking.

Merges sessions from multiple detection sources (agent-task CLI, events API,
reviews API) with two-tier correlation: exact task ID match (primary) and
timestamp-window fallback (60-second tolerance).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from agentic_devtools.cli.ci.tracker.models import (
    DetectionSource,
    TrackedSession,
)

# Timestamp correlation window in seconds
_CORRELATION_WINDOW_SECONDS = 60


def merge_sessions(
    existing: list[TrackedSession],
    new_agent_task: list[TrackedSession] | None = None,
    new_events_api: list[TrackedSession] | None = None,
    new_reviews_api: list[TrackedSession] | None = None,
) -> list[TrackedSession]:
    """Merge sessions from multiple detection sources.

    Uses two-tier correlation:
    1. Exact session_id match (primary)
    2. Timestamp-window fallback (60-second tolerance)

    Args:
        existing: Sessions already tracked in the comment.
        new_agent_task: Newly detected sessions from gh agent-task list.
        new_events_api: Newly detected sessions from events API.
        new_reviews_api: Newly detected sessions from reviews API.

    Returns:
        Merged list of all unique sessions.
    """
    new_agent_task = new_agent_task or []
    new_events_api = new_events_api or []
    new_reviews_api = new_reviews_api or []

    # Build index by session_id for fast lookup
    merged: dict[str, TrackedSession] = {}
    for session in existing:
        merged[session.session_id] = session

    all_new = new_agent_task + new_events_api + new_reviews_api

    for new_session in all_new:
        # Tier 1: Exact session_id match
        if new_session.session_id in merged:
            existing_session = merged[new_session.session_id]
            # Merge sources
            combined_sources = list(existing_session.sources)
            for src in new_session.sources:
                if src not in combined_sources:
                    combined_sources.append(src)
            # Update status if new is more terminal
            status = (
                new_session.status
                if new_session.status and new_session.status != "running"
                else existing_session.status
            )
            # Update dispatch URL if new one has it
            dispatch_url = new_session.dispatch_run_url or existing_session.dispatch_run_url
            merged[new_session.session_id] = replace(
                existing_session,
                sources=combined_sources,
                status=status,
                dispatch_run_url=dispatch_url,
            )
            continue

        # Tier 2: Timestamp-window fallback correlation
        correlated = _find_timestamp_correlation(new_session, list(merged.values()))
        if correlated:
            existing_session = merged[correlated.session_id]
            combined_sources = list(existing_session.sources)
            for src in new_session.sources:
                if src not in combined_sources:
                    combined_sources.append(src)
            merged[correlated.session_id] = replace(
                existing_session,
                sources=combined_sources,
                correlation_id=new_session.session_id,
            )
        else:
            # New unique session
            merged[new_session.session_id] = new_session

    return list(merged.values())


def determine_new_sessions(
    existing: list[TrackedSession],
    merged: list[TrackedSession],
) -> list[TrackedSession]:
    """Determine which sessions are new and require dispatch.

    A session requires dispatch if:
    - It wasn't in the existing list (by session_id)
    - It has a terminal status (not 'running')
    - It doesn't already have a dispatch URL

    Args:
        existing: Sessions from the previous tracker comment.
        merged: Sessions after merging all sources.

    Returns:
        List of sessions that need ai-pr-loop dispatch.
    """
    existing_ids = {s.session_id for s in existing}

    return [s for s in merged if s.session_id not in existing_ids and s.status != "running" and not s.dispatch_run_url]


def is_review_completion(session: TrackedSession) -> bool:
    """Check if a session represents a Copilot review completion.

    Args:
        session: Session to check.

    Returns:
        True if the session is from the reviews API source.
    """
    return DetectionSource.REVIEWS_API in session.sources


def _find_timestamp_correlation(
    target: TrackedSession,
    candidates: list[TrackedSession],
) -> TrackedSession | None:
    """Find a session in candidates within the timestamp correlation window.

    Args:
        target: Session to find a match for.
        candidates: Existing sessions to search.

    Returns:
        Matching session or None.
    """
    if not target.detected_at:
        return None

    try:
        target_dt = _parse_iso(target.detected_at)
    except (ValueError, TypeError):
        return None

    for candidate in candidates:
        if not candidate.detected_at:
            continue
        try:
            candidate_dt = _parse_iso(candidate.detected_at)
        except (ValueError, TypeError):
            continue

        diff = abs((target_dt - candidate_dt).total_seconds())
        if diff <= _CORRELATION_WINDOW_SECONDS:
            return candidate

    return None


def _parse_iso(timestamp: str) -> datetime:
    """Parse an ISO 8601 timestamp string."""
    # Handle both with and without timezone
    if timestamp.endswith("Z"):
        timestamp = timestamp[:-1] + "+00:00"
    return datetime.fromisoformat(timestamp)
