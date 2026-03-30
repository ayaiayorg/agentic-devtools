"""
Submission Manager for file review submissions.

Provides a thread-safe FIFO queue that accepts file review submission payloads,
immediately returns an ACK (the queued SubmissionItem), and processes items
serially via a daemon worker thread. The processor is an injectable Callable
so the core engine is testable in isolation.

Components:
- SubmissionStatus: Enum for item lifecycle states
- SubmissionItem: Dataclass representing a single submission
- SubmissionManager: Queue + worker engine
- create_submission_manager: Convenience factory function
"""

from __future__ import annotations

import queue
import random
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TransientSubmissionError(Exception):
    """Raised by processors to signal a transient/retryable failure."""


class SubmissionStatus(str, Enum):
    """Status values for submission items."""

    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class SubmissionItem:
    """
    Represents a single file review submission.

    Attributes:
        id: Unique identifier (UUID)
        pr_id: Pull request ID
        file_path: Path to the file being reviewed
        outcome: Review outcome (approve, request-changes, request-changes-with-suggestion)
        summary: Review summary text
        suggestions: Optional list of suggestion dicts
        status: Current submission status
        attempts: Number of processing attempts
        error_message: Error message if processing failed
        created_at: ISO UTC timestamp when item was created
        completed_at: ISO UTC timestamp when processing finished
    """

    id: str
    pr_id: int
    file_path: str
    outcome: str
    summary: str
    suggestions: list[dict[str, Any]] | None = None
    status: SubmissionStatus = SubmissionStatus.QUEUED
    attempts: int = 0
    error_message: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert submission item to dictionary for serialization."""
        return {
            "id": self.id,
            "pr_id": self.pr_id,
            "file_path": self.file_path,
            "outcome": self.outcome,
            "summary": self.summary,
            "suggestions": self.suggestions,
            "status": self.status.value if isinstance(self.status, SubmissionStatus) else self.status,
            "attempts": self.attempts,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubmissionItem:
        """Create a SubmissionItem from a dictionary."""
        status_value = data.get("status", SubmissionStatus.QUEUED.value)
        if isinstance(status_value, SubmissionStatus):
            status = status_value
        elif isinstance(status_value, str):
            try:
                status = SubmissionStatus(status_value)
            except ValueError:
                status = SubmissionStatus.QUEUED
        else:
            status = SubmissionStatus.QUEUED

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            pr_id=data.get("pr_id", 0),
            file_path=data.get("file_path", ""),
            outcome=data.get("outcome", ""),
            summary=data.get("summary", ""),
            suggestions=data.get("suggestions"),
            status=status,
            attempts=data.get("attempts", 0),
            error_message=data.get("error_message"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            completed_at=data.get("completed_at"),
        )


@dataclass
class FailedItemSummary:
    """Summary of a single failed submission item."""

    item_id: str
    file_path: str
    last_error: str
    attempts: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "item_id": self.item_id,
            "file_path": self.file_path,
            "last_error": self.last_error,
            "attempts": self.attempts,
        }


@dataclass
class FailureReport:
    """Consolidated report of all failed submission items."""

    failed_items: list[FailedItemSummary]
    resubmission_guidance: str = (
        "Review the errors above. Transient failures may succeed"
        " on resubmission. Use enqueue() to resubmit failed items."
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "failed_items": [item.to_dict() for item in self.failed_items],
            "resubmission_guidance": self.resubmission_guidance,
        }

    def to_text(self) -> str:
        """Render a human-readable text report."""
        lines: list[str] = ["Failed Submissions:"]
        for item in self.failed_items:
            lines.append(f"  - {item.file_path}: {item.last_error} (attempts: {item.attempts}, id: {item.item_id})")
        lines.append("")
        lines.append(self.resubmission_guidance)
        return "\n".join(lines)


def _default_processor(item: SubmissionItem) -> None:
    """Default no-op processor. Item is marked succeeded by the worker loop."""


class SubmissionManager:
    """
    Thread-safe FIFO queue for file review submissions.

    Accepts submission payloads via enqueue(), immediately returns the queued
    SubmissionItem, and processes items serially in a background daemon thread
    through an injected processor callable.

    This class retains all enqueued items in memory for status introspection.
    It is designed for short-lived, per-session use (e.g., one manager per PR
    review). Callers that need long-lived managers should periodically discard
    completed items or create fresh instances.
    """

    def __init__(
        self,
        processor: Callable[[SubmissionItem], None] | None = None,
        max_retries: int = 3,
        backoff_base: float = 1.0,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if backoff_base <= 0:
            raise ValueError("backoff_base must be > 0")
        self._processor: Callable[[SubmissionItem], None] = processor or _default_processor
        self._queue: queue.Queue[SubmissionItem | None] = queue.Queue()
        self._items: dict[str, SubmissionItem] = {}
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._shutdown_event = threading.Event()
        self._max_retries = max_retries
        self._backoff_base = backoff_base

    def enqueue(
        self,
        pr_id: int,
        file_path: str,
        outcome: str,
        summary: str,
        suggestions: list[dict[str, Any]] | None = None,
    ) -> SubmissionItem:
        """
        Create and enqueue a submission item.

        Returns immediately with the queued SubmissionItem. Lazily starts
        the worker thread on the first call.

        Args:
            pr_id: Pull request ID
            file_path: Path to the file being reviewed
            outcome: Review outcome
            summary: Review summary text
            suggestions: Optional list of suggestion dicts

        Returns:
            The created SubmissionItem (initially status=QUEUED).  Because the
            worker thread starts immediately, the returned object may have
            already transitioned to PROCESSING or SUCCEEDED by the time the
            caller inspects it.

        Raises:
            RuntimeError: If the manager has been shut down
        """
        item = SubmissionItem(
            id=str(uuid.uuid4()),
            pr_id=pr_id,
            file_path=file_path,
            outcome=outcome,
            summary=summary,
            suggestions=suggestions,
        )

        with self._lock:
            if self._shutdown_event.is_set():
                raise RuntimeError("SubmissionManager has been shut down")
            self._items[item.id] = item
            self._queue.put(item)

        self._ensure_worker_started()

        return item

    def get_item(self, item_id: str) -> SubmissionItem | None:
        """Look up a submission by ID.

        Returns:
            The SubmissionItem if found, None otherwise
        """
        with self._lock:
            return self._items.get(item_id)

    def get_items_by_pr(self, pr_id: int) -> list[SubmissionItem]:
        """Return all items for a given PR ID.

        Args:
            pr_id: Pull request ID to filter by

        Returns:
            List of SubmissionItems for the given PR (may be empty)
        """
        with self._lock:
            return [item for item in self._items.values() if item.pr_id == pr_id]

    def get_queue_depth(self) -> int:
        """Return the number of items currently marked as queued.

        This counts items whose status is still ``QUEUED`` in the manager's
        internal state. Because the worker thread dequeues items from the
        underlying queue before updating their status to ``PROCESSING``,
        this value is an approximate debugging metric rather than a precise
        reflection of the underlying queue's contents at any given instant.
        """
        with self._lock:
            return sum(1 for item in self._items.values() if item.status == SubmissionStatus.QUEUED)

    def get_failure_report(self) -> FailureReport | None:
        """Return a consolidated report of all failed items.

        Returns:
            FailureReport if any items have status FAILED, None otherwise
        """
        with self._lock:
            failed = [item for item in self._items.values() if item.status == SubmissionStatus.FAILED]
        if not failed:
            return None
        return FailureReport(
            failed_items=[
                FailedItemSummary(
                    item_id=item.id,
                    file_path=item.file_path,
                    last_error=item.error_message or "",
                    attempts=item.attempts,
                )
                for item in failed
            ]
        )

    def shutdown(self, wait: bool = True) -> FailureReport | None:
        """Signal the worker thread to stop.

        If wait=True, blocks until the worker thread has finished processing
        the current item and exited, then returns a FailureReport if any items
        failed (or None if all succeeded). Multiple calls are idempotent
        w.r.t. the shutdown signal, but subsequent calls with wait=True will
        still join the worker thread.

        Args:
            wait: Whether to block until the worker exits

        Returns:
            FailureReport if any items failed (only when wait=True), else None
        """
        worker: threading.Thread | None = None
        with self._lock:
            if not self._shutdown_event.is_set():
                self._shutdown_event.set()
                # Enqueue sentinel under the same lock used by enqueue()
                # to prevent interleavings where the sentinel appears
                # before a newly queued item.
                self._queue.put(None)
            worker = self._worker

        if wait:
            if worker is None:
                # A concurrent enqueue() may have queued items but not yet
                # called _ensure_worker_started().  Start the worker so
                # there is a thread to join (it will drain the queue and
                # then see the sentinel).
                self._ensure_worker_started()
                worker = self._worker
            if worker is not None and worker.is_alive():
                worker.join()
            return self.get_failure_report()

        return None

    def _ensure_worker_started(self) -> None:
        """Start the worker thread if not already running."""
        # Fast-path check without lock, followed by a locked double-check to
        # prevent multiple concurrent enqueue() calls from starting multiple workers.
        if self._worker is None or not self._worker.is_alive():
            with self._lock:
                if self._worker is None or not self._worker.is_alive():
                    self._worker = threading.Thread(target=self._worker_loop, daemon=True)
                    self._worker.start()

    def _worker_loop(self) -> None:
        """Process items from the queue serially, retrying transient failures."""
        while True:
            item = self._queue.get()
            try:
                if item is None:
                    # Sentinel received — exit the loop
                    break

                with self._lock:
                    item.status = SubmissionStatus.PROCESSING
                    item.attempts = 1

                while True:
                    try:
                        self._processor(item)
                        with self._lock:
                            item.status = SubmissionStatus.SUCCEEDED
                            item.completed_at = datetime.now(timezone.utc).isoformat()
                        break
                    except TransientSubmissionError as exc:
                        with self._lock:
                            item.error_message = str(exc)
                        if item.attempts >= self._max_retries + 1:
                            with self._lock:
                                item.status = SubmissionStatus.FAILED
                                item.completed_at = datetime.now(timezone.utc).isoformat()
                            break
                        with self._lock:
                            item.status = SubmissionStatus.RETRYING
                        delay = self._backoff_base * (2 ** (item.attempts - 1)) + random.uniform(0, 1.0)
                        interrupted = self._shutdown_event.wait(delay)
                        if interrupted:
                            with self._lock:
                                item.status = SubmissionStatus.FAILED
                                item.completed_at = datetime.now(timezone.utc).isoformat()
                            break
                        with self._lock:
                            item.status = SubmissionStatus.PROCESSING
                            item.attempts += 1
                    except Exception as exc:
                        with self._lock:
                            item.status = SubmissionStatus.FAILED
                            item.error_message = str(exc)
                            item.completed_at = datetime.now(timezone.utc).isoformat()
                        break
            finally:
                self._queue.task_done()


def create_submission_manager(
    processor: Callable[[SubmissionItem], None] | None = None,
    max_retries: int = 3,
    backoff_base: float = 1.0,
) -> SubmissionManager:
    """Convenience factory for creating a SubmissionManager.

    Args:
        processor: Optional callable to process each submission item.
                   Defaults to a no-op processor.
        max_retries: Maximum number of retries for transient errors (default 3).
        backoff_base: Base delay in seconds for exponential backoff (default 1.0).

    Returns:
        A new SubmissionManager instance
    """
    return SubmissionManager(
        processor=processor,
        max_retries=max_retries,
        backoff_base=backoff_base,
    )
