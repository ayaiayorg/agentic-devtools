"""Tests for agentic_devtools.submission_manager.SubmissionManager."""

import threading
import time

import pytest

from agentic_devtools.submission_manager import SubmissionItem, SubmissionManager, SubmissionStatus


class TestSubmissionManager:
    """Tests for SubmissionManager class."""

    def test_enqueue_returns_immediately_with_queued_item(self):
        """Verify returned item has status=queued and a valid id."""
        barrier = threading.Event()

        def blocking_processor(item: SubmissionItem) -> None:
            barrier.wait(timeout=5)

        manager = SubmissionManager(processor=blocking_processor)
        try:
            manager.enqueue(
                pr_id=100,
                file_path="/src/app.ts",
                outcome="approve",
                summary="LGTM",
            )
            # The first item may already be picked up, but it blocks in the
            # processor, so enqueue a second item whose status we can assert
            item2 = manager.enqueue(
                pr_id=100,
                file_path="/src/other.ts",
                outcome="approve",
                summary="Also LGTM",
            )
            assert item2.status == SubmissionStatus.QUEUED
            assert item2.id is not None
            assert len(item2.id) == 36  # UUID format
            assert item2.pr_id == 100
            assert item2.file_path == "/src/other.ts"
            assert item2.outcome == "approve"
            assert item2.summary == "Also LGTM"
        finally:
            barrier.set()
            manager.shutdown(wait=True)

    def test_serial_processing_order(self):
        """Enqueue 3+ items, verify processing order matches enqueue order."""
        order: list[str] = []
        lock = threading.Lock()

        def recording_processor(item: SubmissionItem) -> None:
            with lock:
                order.append(item.file_path)

        manager = SubmissionManager(processor=recording_processor)
        try:
            manager.enqueue(pr_id=1, file_path="file_1", outcome="approve", summary="s1")
            manager.enqueue(pr_id=1, file_path="file_2", outcome="approve", summary="s2")
            manager.enqueue(pr_id=1, file_path="file_3", outcome="approve", summary="s3")
        finally:
            manager.shutdown(wait=True)

        assert order == ["file_1", "file_2", "file_3"]

    def test_processor_called_with_item(self):
        """Verify the injected processor receives the correct SubmissionItem."""
        received_items: list[SubmissionItem] = []

        def capturing_processor(item: SubmissionItem) -> None:
            received_items.append(item)

        manager = SubmissionManager(processor=capturing_processor)
        try:
            enqueued = manager.enqueue(
                pr_id=42,
                file_path="/src/service.ts",
                outcome="request-changes",
                summary="Issues found",
                suggestions=[{"line": 10, "content": "Fix"}],
            )
        finally:
            manager.shutdown(wait=True)

        assert len(received_items) == 1
        assert received_items[0].id == enqueued.id
        assert received_items[0].file_path == "/src/service.ts"
        assert received_items[0].suggestions == [{"line": 10, "content": "Fix"}]

    def test_item_transitions_to_succeeded(self):
        """Enqueue, shutdown, verify status=succeeded, attempts=1, completed_at set."""
        manager = SubmissionManager()
        try:
            item = manager.enqueue(
                pr_id=1,
                file_path="/file.ts",
                outcome="approve",
                summary="ok",
            )
        finally:
            manager.shutdown(wait=True)

        assert item.status == SubmissionStatus.SUCCEEDED
        assert item.attempts == 1
        assert item.completed_at is not None

    def test_item_transitions_to_failed_on_exception(self):
        """Processor raises ValueError; verify status=failed, error_message, attempts=1."""

        def failing_processor(item: SubmissionItem) -> None:
            raise ValueError("Test error: API call failed")

        manager = SubmissionManager(processor=failing_processor)
        try:
            item = manager.enqueue(
                pr_id=1,
                file_path="/file.ts",
                outcome="approve",
                summary="ok",
            )
        finally:
            manager.shutdown(wait=True)

        assert item.status == SubmissionStatus.FAILED
        assert item.error_message == "Test error: API call failed"
        assert item.attempts == 1
        assert item.completed_at is not None

    def test_failed_item_does_not_stop_worker(self):
        """Enqueue 2 items, first fails, second succeeds."""
        call_count = 0

        def selective_processor(item: SubmissionItem) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("First item fails")

        manager = SubmissionManager(processor=selective_processor)
        try:
            item1 = manager.enqueue(pr_id=1, file_path="fail.ts", outcome="approve", summary="s1")
            item2 = manager.enqueue(pr_id=1, file_path="pass.ts", outcome="approve", summary="s2")
        finally:
            manager.shutdown(wait=True)

        assert item1.status == SubmissionStatus.FAILED
        assert item2.status == SubmissionStatus.SUCCEEDED

    def test_get_item_returns_item(self):
        """Enqueue and retrieve by ID."""
        manager = SubmissionManager()
        try:
            item = manager.enqueue(pr_id=1, file_path="/file.ts", outcome="approve", summary="ok")
            found = manager.get_item(item.id)
        finally:
            manager.shutdown(wait=True)

        assert found is not None
        assert found.id == item.id

    def test_get_item_returns_none_for_unknown_id(self):
        """Verify None for nonexistent ID."""
        manager = SubmissionManager()
        try:
            result = manager.get_item("nonexistent-id")
        finally:
            manager.shutdown(wait=True)

        assert result is None

    def test_get_items_by_pr(self):
        """Enqueue items for 2 different PR IDs, verify filtering."""
        manager = SubmissionManager()
        try:
            manager.enqueue(pr_id=100, file_path="a.ts", outcome="approve", summary="s1")
            manager.enqueue(pr_id=200, file_path="b.ts", outcome="approve", summary="s2")
            manager.enqueue(pr_id=100, file_path="c.ts", outcome="approve", summary="s3")
        finally:
            manager.shutdown(wait=True)

        pr100_items = manager.get_items_by_pr(100)
        pr200_items = manager.get_items_by_pr(200)
        pr999_items = manager.get_items_by_pr(999)

        assert len(pr100_items) == 2
        assert all(item.pr_id == 100 for item in pr100_items)
        assert len(pr200_items) == 1
        assert pr200_items[0].pr_id == 200
        assert len(pr999_items) == 0

    def test_get_queue_depth(self):
        """Enqueue items with a blocking processor, check depth > 0."""
        barrier = threading.Event()
        processing_started = threading.Event()

        def blocking_processor(item: SubmissionItem) -> None:
            processing_started.set()
            barrier.wait(timeout=5)

        manager = SubmissionManager(processor=blocking_processor)
        try:
            # Enqueue first item — it will block in the processor
            manager.enqueue(pr_id=1, file_path="first.ts", outcome="approve", summary="s1")
            # Wait until the worker has picked up the first item
            processing_started.wait(timeout=5)

            # Enqueue more items — they should be waiting in the queue
            manager.enqueue(pr_id=1, file_path="second.ts", outcome="approve", summary="s2")
            manager.enqueue(pr_id=1, file_path="third.ts", outcome="approve", summary="s3")

            assert manager.get_queue_depth() >= 2
        finally:
            barrier.set()
            manager.shutdown(wait=True)

    def test_shutdown_wait_blocks_until_complete(self):
        """Verify shutdown returns only after worker exits."""
        processed = threading.Event()

        def slow_processor(item: SubmissionItem) -> None:
            time.sleep(0.05)
            processed.set()

        manager = SubmissionManager(processor=slow_processor)
        manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")
        manager.shutdown(wait=True)

        assert processed.is_set()
        assert manager._worker is not None
        assert not manager._worker.is_alive()

    def test_shutdown_is_idempotent(self):
        """Call shutdown() twice, no error."""
        manager = SubmissionManager()
        manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")
        manager.shutdown(wait=True)
        manager.shutdown(wait=True)  # second call should be a no-op

    def test_shutdown_wait_true_after_wait_false(self):
        """shutdown(wait=True) still joins worker even after shutdown(wait=False)."""
        barrier = threading.Event()

        def blocking_processor(item: SubmissionItem) -> None:
            barrier.wait(timeout=5)

        manager = SubmissionManager(processor=blocking_processor)
        manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")

        # First shutdown without waiting — signals but doesn't join
        manager.shutdown(wait=False)
        assert manager._worker is not None
        assert manager._worker.is_alive()

        # Release the processor so the worker can finish
        barrier.set()

        # Second shutdown with wait — must still join the worker
        manager.shutdown(wait=True)
        assert not manager._worker.is_alive()

    def test_enqueue_after_shutdown_raises(self):
        """Verify RuntimeError when enqueueing after shutdown."""
        manager = SubmissionManager()
        manager.shutdown(wait=True)

        with pytest.raises(RuntimeError, match="SubmissionManager has been shut down"):
            manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")

    def test_default_processor_succeeds(self):
        """Create manager without processor arg, enqueue, verify item succeeds."""
        manager = SubmissionManager()
        try:
            item = manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")
        finally:
            manager.shutdown(wait=True)

        assert item.status == SubmissionStatus.SUCCEEDED

    def test_worker_thread_is_daemon(self):
        """Verify the worker thread has daemon=True."""
        manager = SubmissionManager()
        try:
            manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")
            # Wait deterministically for the worker thread to be created
            start = time.time()
            while manager._worker is None and time.time() - start < 1.0:
                time.sleep(0.005)
            assert manager._worker is not None, "Worker thread was not started within timeout"
            assert manager._worker.daemon is True
        finally:
            manager.shutdown(wait=True)
