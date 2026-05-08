"""Data classes for the finalization pass."""

from __future__ import annotations

from dataclasses import dataclass, field

# Composite key type: (thread_id, comment_id) — unique across all threads.
# Azure DevOps comment IDs are per-thread (e.g. the first comment in every
# thread is id=1), so comment_id alone is NOT unique.
CommentKey = tuple[int, int]


def comment_key(comment: EligibleComment) -> CommentKey:
    """Return the composite key ``(thread_id, comment_id)`` for *comment*."""
    return (comment.thread_id, comment.comment_id)


@dataclass
class EligibleComment:
    """A single AGDT-generated comment eligible for finalization."""

    thread_id: int
    comment_id: int
    marker_type: str
    marker_data: dict[str, str]
    current_content: str
    file_path: str | None = None


@dataclass
class EligibleComments:
    """Classified eligible comments grouped by type."""

    file_summaries: list[EligibleComment] = field(default_factory=list)
    overall_summary: EligibleComment | None = None
    activity_log_entries: list[EligibleComment] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)


@dataclass
class ConvergenceResult:
    """Result of a convergence check for a single comment."""

    comment: EligibleComment
    converged: bool
    expected_content: str
    observed_content: str


@dataclass
class BatchRepairResult:
    """Result of the batch repair pass."""

    attempted: int = 0
    succeeded: int = 0
    failed: int = 0
    activity_log_completed: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class TargetedRepairResult:
    """Result of the targeted (per-comment PATCH) repair pass."""

    attempted: int = 0
    succeeded: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class FinalizationReport:
    """Final report from the finalization pass."""

    status: str  # "success", "partial", "no-op", "failure", "skipped"
    repaired: int = 0
    skipped: int = 0
    unchanged: int = 0
    failed: int = 0
    details: list[str] = field(default_factory=list)
    duration_ms: int = 0

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dictionary."""
        return {
            "status": self.status,
            "repaired": self.repaired,
            "skipped": self.skipped,
            "unchanged": self.unchanged,
            "failed": self.failed,
            "details": self.details,
            "duration_ms": self.duration_ms,
        }
