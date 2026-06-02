"""Data models for the segments module."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SegmentStatus(str, Enum):
    """Status values for state segments."""

    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        """Return True if this status is a terminal state."""
        return self in (SegmentStatus.COMPLETED, SegmentStatus.FAILED)


@dataclass
class StateSegment:
    """Represents an isolated state segment owned by a single worker."""

    segment_id: str
    owner_worker_id: str
    owner_pid: int
    created_utc: str
    status: SegmentStatus
    data: dict[str, Any] = field(default_factory=dict)
    completed_utc: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary suitable for JSON persistence."""
        return {
            "segment_id": self.segment_id,
            "owner_worker_id": self.owner_worker_id,
            "owner_pid": self.owner_pid,
            "created_utc": self.created_utc,
            "status": self.status.value,
            "data": self.data,
            "completed_utc": self.completed_utc,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StateSegment:
        """Deserialize from a dictionary."""
        return cls(
            segment_id=data["segment_id"],
            owner_worker_id=data["owner_worker_id"],
            owner_pid=data["owner_pid"],
            created_utc=data["created_utc"],
            status=SegmentStatus(data["status"]),
            data=data.get("data", {}),
            completed_utc=data.get("completed_utc"),
            error=data.get("error"),
        )
