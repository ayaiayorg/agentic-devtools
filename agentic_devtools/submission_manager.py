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
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SubmissionStatus(str, Enum):
    """Status values for submission items."""

    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


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


def _default_processor(item: SubmissionItem) -> None:
    """Default no-op processor. Item is marked succeeded by the worker loop."""


class SubmissionManager:
    """
    Thread-safe FIFO queue for file review submissions.

    Accepts submission payloads via enqueue(), immediately returns the queued
    SubmissionItem, and processes items serially in a background daemon thread
    through an injected processor callable.
    """

    def __init__(self, processor: Callable[[SubmissionItem], None] | None = None) -> None:
        self._processor: Callable[[SubmissionItem], None] = processor or _default_processor
        self._queue: queue.Queue[SubmissionItem | None] = queue.Queue()
        self._items: dict[str, SubmissionItem] = {}
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._shutdown_event = threading.Event()

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
            The created SubmissionItem with status=queued

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
        """Return the number of items waiting in the queue (not yet picked up)."""
        with self._lock:
            return sum(1 for item in self._items.values() if item.status == SubmissionStatus.QUEUED)

    def shutdown(self, wait: bool = True) -> None:
        """Signal the worker thread to stop.

        If wait=True, blocks until the worker thread has finished processing
        the current item and exited. Multiple calls are idempotent w.r.t. the
        shutdown signal, but subsequent calls with wait=True will still join
        the worker thread.

        Args:
            wait: Whether to block until the worker exits
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

        if wait and worker is not None and worker.is_alive():
            worker.join()

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
        """Process items from the queue serially."""
        while True:
            item = self._queue.get()
            try:
                if item is None:
                    # Sentinel received — exit the loop
                    break

                with self._lock:
                    item.status = SubmissionStatus.PROCESSING
                    item.attempts += 1

                try:
                    self._processor(item)
                    with self._lock:
                        item.status = SubmissionStatus.SUCCEEDED
                        item.completed_at = datetime.now(timezone.utc).isoformat()
                except Exception as exc:
                    with self._lock:
                        item.status = SubmissionStatus.FAILED
                        item.error_message = str(exc)
                        item.completed_at = datetime.now(timezone.utc).isoformat()
            finally:
                self._queue.task_done()


def create_submission_manager(
    processor: Callable[[SubmissionItem], None] | None = None,
) -> SubmissionManager:
    """Convenience factory for creating a SubmissionManager.

    Args:
        processor: Optional callable to process each submission item.
                   Defaults to a no-op processor.

    Returns:
        A new SubmissionManager instance
    """
    return SubmissionManager(processor=processor)
