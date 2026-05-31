"""Parser for agent session tracker comments."""

from __future__ import annotations

import re

from agentic_devtools.cli.ci.tracker.models import (
    TRACKER_MARKER_PREFIX,
    DetectionSource,
    TrackedSession,
    TrackerComment,
)


def parse_tracker_comment(body: str) -> TrackerComment:
    """Parse a tracker comment body into a TrackerComment.

    Args:
        body: Raw comment body string.

    Returns:
        Parsed TrackerComment. If the body is empty or doesn't contain the
        marker, returns an empty TrackerComment with the raw_body set.
    """
    comment = TrackerComment(raw_body=body)

    if not body or TRACKER_MARKER_PREFIX not in body:
        return comment

    # Parse HTML comment header for metadata
    header_match = re.search(r"<!-- agent-session-tracker\n(.*?)-->", body, re.DOTALL)
    if header_match:
        header_content = header_match.group(1)
        last_checked_match = re.search(r"last_checked=(.+)", header_content)
        if last_checked_match:
            comment.last_checked = last_checked_match.group(1).strip()

    # Parse PR number from heading
    pr_match = re.search(r"#(\d+)", body)
    if pr_match:
        comment.pr_number = int(pr_match.group(1))

    # Parse table rows (skip header and separator)
    table_lines = [
        line.strip()
        for line in body.split("\n")
        if line.strip().startswith("|")
        and not line.strip().startswith("| Session ID")
        and not re.match(r"^\|[-|\s]+\|$", line.strip())
    ]

    for line in table_lines:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) >= 5:
            session_id = cells[0]
            source_str = cells[1]
            status = cells[2]
            detected_at = cells[3]
            dispatch_cell = cells[4]

            # Parse source (may be comma-separated for multi-source sessions)
            sources = []
            for token in (t.strip() for t in source_str.split(",")):
                if not token or token == "—":
                    continue
                try:
                    sources.append(DetectionSource(token))
                except ValueError:
                    pass

            # Parse dispatch URL from markdown link
            dispatch_url = ""
            link_match = re.search(r"\[.*?\]\((.*?)\)", dispatch_cell)
            if link_match:
                dispatch_url = link_match.group(1)

            session = TrackedSession(
                session_id=session_id,
                sources=sources,
                status=status,
                detected_at=detected_at,
                dispatch_run_url=dispatch_url,
            )
            comment.sessions.append(session)

    return comment
