"""Platform-agnostic protocols for the tiered thread resolution system.

Defines structural interfaces (Protocol classes) that allow any CI platform
(GitHub, AzureDevOps, Jira) to integrate with the resolution engine without
coupling to platform-specific types.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from agentic_devtools.cli.ci.resolution.models import TierResult


@runtime_checkable
class ThreadComment(Protocol):
    """A single comment within a review thread."""

    @property
    def body(self) -> str:
        """Comment body text."""
        ...  # pragma: no cover

    @property
    def created_at(self) -> str:
        """ISO 8601 timestamp of comment creation."""
        ...  # pragma: no cover

    @property
    def author_login(self) -> str | None:
        """Login of the comment author, or None if unknown."""
        ...  # pragma: no cover


@runtime_checkable
class ResolutionContext(Protocol):
    """Contextual data needed for thread evaluation."""

    @property
    def diff_text(self) -> str:
        """Unified diff between the review commit and HEAD."""
        ...  # pragma: no cover

    @property
    def head_commit_oid(self) -> str:
        """Current HEAD commit OID."""
        ...  # pragma: no cover


@runtime_checkable
class ReviewThread(Protocol):
    """A review thread with all metadata needed for tiered evaluation."""

    @property
    def thread_id(self) -> str:
        """Unique thread identifier (platform-specific)."""
        ...  # pragma: no cover

    @property
    def file_path(self) -> str | None:
        """File path the thread is attached to, or None for PR-level comments."""
        ...  # pragma: no cover

    @property
    def start_line(self) -> int | None:
        """Start line of the comment range (1-based), or None."""
        ...  # pragma: no cover

    @property
    def end_line(self) -> int | None:
        """End line of the comment range (1-based), or None."""
        ...  # pragma: no cover

    @property
    def is_outdated(self) -> bool | None:
        """Whether the platform considers this thread outdated (tri-state)."""
        ...  # pragma: no cover

    @property
    def comments(self) -> list[ThreadComment]:
        """All comments in the thread, ordered chronologically."""
        ...  # pragma: no cover

    @property
    def originating_review_commit_oid(self) -> str:
        """Commit OID of the review that originated this thread."""
        ...  # pragma: no cover


@runtime_checkable
class EvaluationTier(Protocol):
    """A single tier in the resolution evaluation pipeline."""

    @property
    def name(self) -> str:
        """Human-readable tier name for logging and audit."""
        ...  # pragma: no cover

    def evaluate(self, thread: ReviewThread, context: ResolutionContext) -> TierResult | None:
        """Evaluate a thread and return a result, or None to fall through.

        Returns:
            TierResult if this tier can make a determination, None otherwise.
        """
        ...  # pragma: no cover


@runtime_checkable
class ThreadResolver(Protocol):
    """Interface for resolving threads on a platform."""

    def resolve_thread(self, thread_id: str) -> bool:
        """Resolve a single thread. Returns True on success."""
        ...  # pragma: no cover

    def post_reply(self, thread_id: str, body: str) -> bool:
        """Post a reply to a thread. Returns True on success."""
        ...  # pragma: no cover
