"""Renderer for agent session tracker comments."""

from __future__ import annotations

from datetime import datetime, timezone

from agentic_devtools.cli.ci.tracker.models import (
    TRACKER_MARKER_PREFIX,
    TrackedSession,
    TrackerComment,
)

# GitHub comment size limit (65535 chars), but we use a conservative limit
_MAX_COMMENT_CHARS = 32000

# Maximum completed sessions to keep when truncating
_MAX_COMPLETED_SESSIONS = 20


def render_tracker_comment(comment: TrackerComment) -> str:
    """Render a TrackerComment into a markdown comment body.

    Args:
        comment: TrackerComment to render.

    Returns:
        Formatted markdown string suitable for a PR comment.
    """
    last_checked = comment.last_checked or datetime.now(timezone.utc).isoformat()

    lines = [
        f"{TRACKER_MARKER_PREFIX}last_checked={last_checked}\n-->",
        f"## Agent Sessions for PR #{comment.pr_number}",
        "",
        "| Session ID | Source | Status | Detected At | ai-pr-loop Dispatch |",
        "|---|---|---|---|---|",
    ]

    # Sort sessions: running first, then most recent first
    running = [s for s in comment.sessions if s.status == "running"]
    completed = [s for s in comment.sessions if s.status != "running"]
    completed.sort(key=lambda s: s.detected_at or "", reverse=True)
    sorted_sessions = running + completed

    for session in sorted_sessions:
        source_str = ", ".join(str(s) for s in session.sources) if session.sources else "—"
        dispatch_str = f"[run]({session.dispatch_run_url})" if session.dispatch_run_url else "—"
        lines.append(
            f"| {session.session_id} | {source_str} | {session.status} | {session.detected_at} | {dispatch_str} |"
        )

    return "\n".join(lines)


def truncate_sessions(
    sessions: list[TrackedSession],
) -> list[TrackedSession]:
    """Truncate sessions to fit within comment size limits.

    Preserves all running sessions and the 20 most recent completed sessions.
    This ensures the rendered comment stays under the 32K character limit.

    Args:
        sessions: Full list of sessions.

    Returns:
        Truncated list of sessions.
    """
    running = [s for s in sessions if s.status == "running"]
    completed = [s for s in sessions if s.status != "running"]

    # Sort completed by detected_at descending (most recent first)
    completed.sort(key=lambda s: s.detected_at or "", reverse=True)

    # Keep all running + most recent completed
    kept_completed = completed[:_MAX_COMPLETED_SESSIONS]

    result = running + kept_completed

    # If still too large, further truncate completed
    # Build a test render to check size
    test_comment = TrackerComment(sessions=result)
    rendered = render_tracker_comment(test_comment)
    while len(rendered) > _MAX_COMMENT_CHARS and kept_completed:
        kept_completed.pop()
        result = running + kept_completed
        test_comment = TrackerComment(sessions=result)
        rendered = render_tracker_comment(test_comment)

    return result
