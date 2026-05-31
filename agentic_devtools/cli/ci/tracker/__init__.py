"""Agent session tracker — comment-based deduplication for session monitoring.

Provides reusable logic for reading/writing/updating tracker comments on PRs,
session deduplication (by task ID and event ID), and merging data from both
detection sources (agent-task CLI and events API).
"""

from __future__ import annotations

from agentic_devtools.cli.ci.tracker.merger import (
    determine_new_sessions,
    is_review_completion,
    merge_sessions,
)
from agentic_devtools.cli.ci.tracker.models import (
    DetectionSource,
    TrackedSession,
    TrackerComment,
)
from agentic_devtools.cli.ci.tracker.parser import parse_tracker_comment
from agentic_devtools.cli.ci.tracker.renderer import (
    render_tracker_comment,
    truncate_sessions,
)

__all__ = [
    "DetectionSource",
    "TrackedSession",
    "TrackerComment",
    "determine_new_sessions",
    "is_review_completion",
    "merge_sessions",
    "parse_tracker_comment",
    "render_tracker_comment",
    "truncate_sessions",
]
