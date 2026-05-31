"""Data models for agent session tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DetectionSource(Enum):
    """Source that detected an agent session."""

    AGENT_TASK = "agent-task"
    EVENTS_API = "events-api"
    REVIEWS_API = "reviews-api"

    def __str__(self) -> str:
        return self.value


@dataclass
class TrackedSession:
    """A single tracked agent session."""

    session_id: str
    sources: list[DetectionSource] = field(default_factory=list)
    status: str = ""
    detected_at: str = ""
    dispatch_run_url: str = ""
    pr_number: int = 0
    correlation_id: str = ""

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON interchange."""
        return {
            "session_id": self.session_id,
            "sources": [s.value for s in self.sources],
            "status": self.status,
            "detected_at": self.detected_at,
            "dispatch_run_url": self.dispatch_run_url,
            "pr_number": self.pr_number,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TrackedSession:
        """Deserialize from dictionary."""
        return cls(
            session_id=data["session_id"],
            sources=[DetectionSource(s) for s in data.get("sources", [])],
            status=data.get("status", ""),
            detected_at=data.get("detected_at", ""),
            dispatch_run_url=data.get("dispatch_run_url", ""),
            pr_number=data.get("pr_number", 0),
            correlation_id=data.get("correlation_id", ""),
        )


@dataclass
class TrackerComment:
    """Represents the full tracker comment on a PR."""

    comment_id: int | None = None
    pr_number: int = 0
    last_checked: str = ""
    sessions: list[TrackedSession] = field(default_factory=list)
    raw_body: str = ""

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON interchange."""
        return {
            "comment_id": self.comment_id,
            "pr_number": self.pr_number,
            "last_checked": self.last_checked,
            "sessions": [s.to_dict() for s in self.sessions],
        }

    @classmethod
    def from_dict(cls, data: dict) -> TrackerComment:
        """Deserialize from dictionary."""
        return cls(
            comment_id=data.get("comment_id"),
            pr_number=data.get("pr_number", 0),
            last_checked=data.get("last_checked", ""),
            sessions=[TrackedSession.from_dict(s) for s in data.get("sessions", [])],
        )


TRACKER_MARKER_PREFIX = "<!-- agent-session-tracker\n"
"""Marker prefix used to identify tracker comments on PRs."""
