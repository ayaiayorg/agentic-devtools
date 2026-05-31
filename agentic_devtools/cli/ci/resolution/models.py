"""Data models for the tiered thread resolution system.

Contains enums and dataclasses representing resolution verdicts, tier results,
structured replies, and thread resolution state.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


class ResolutionVerdict(enum.Enum):
    """Verdict produced by the resolution engine for a thread."""

    RESOLVE = "RESOLVE"
    UNRESOLVE = "UNRESOLVE"
    TENTATIVE = "TENTATIVE"
    ABANDONED = "ABANDONED"


@dataclass(frozen=True)
class TierResult:
    """Result from a single evaluation tier.

    Attributes:
        verdict: The resolution verdict.
        confidence: Confidence level ("high", "medium", "low").
        tier_name: Name of the tier that produced this result.
        explanation: Human-readable explanation of the rationale.
    """

    verdict: ResolutionVerdict
    confidence: str
    tier_name: str
    explanation: str


@dataclass(frozen=True)
class ResolutionReply:
    """Structured reply to post on a resolved/tentative thread.

    Attributes:
        html_marker: HTML comment marker for machine parsing.
        human_text: Human-readable explanation body.
        model_id: Model identifier (for SDK tier), or None.
    """

    html_marker: str
    human_text: str
    model_id: str | None = None


@dataclass
class ThreadResolutionState:
    """Persistent state for a thread's resolution lifecycle.

    Attributes:
        thread_id: Unique thread identifier.
        verdict: Current resolution verdict.
        tier_name: Tier that produced the verdict.
        confidence: Confidence level of the verdict.
        timestamp: When the verdict was first produced.
        iteration_count: Number of pipeline iterations since first verdict.
        max_iterations: Maximum iterations before expiry.
        max_age_hours: Maximum age in hours before expiry.
    """

    thread_id: str
    verdict: ResolutionVerdict
    tier_name: str
    confidence: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    iteration_count: int = 0
    max_iterations: int = 5
    max_age_hours: float = 24.0

    def is_expired(self) -> bool:
        """Check whether this tentative state has exceeded its TTL."""
        if self.iteration_count >= self.max_iterations:
            return True
        try:
            created = datetime.fromisoformat(self.timestamp)
            now = datetime.now(timezone.utc)
            elapsed_hours = (now - created).total_seconds() / 3600
            return elapsed_hours >= self.max_age_hours
        except (ValueError, TypeError):
            return True

    def increment_iteration(self) -> None:
        """Increment the iteration counter."""
        self.iteration_count += 1

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "thread_id": self.thread_id,
            "verdict": self.verdict.value,
            "tier_name": self.tier_name,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "iteration_count": self.iteration_count,
            "max_iterations": self.max_iterations,
            "max_age_hours": self.max_age_hours,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ThreadResolutionState:
        """Deserialize from a dictionary."""
        return cls(
            thread_id=data["thread_id"],
            verdict=ResolutionVerdict(data["verdict"]),
            tier_name=data["tier_name"],
            confidence=data["confidence"],
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            iteration_count=data.get("iteration_count", 0),
            max_iterations=data.get("max_iterations", 5),
            max_age_hours=data.get("max_age_hours", 24.0),
        )
