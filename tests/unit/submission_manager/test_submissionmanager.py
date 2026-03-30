"""Tests for agentic_devtools.submission_manager.SubmissionManager."""

import threading
import time

import pytest

from agentic_devtools.submission_manager import (
    FailureReport,
    SubmissionItem,
    SubmissionManager,
    SubmissionStatus,
    TransientSubmissionError,
    create_submission_manager,
)

_TERMINAL = (SubmissionStatus.SUCCEEDED, SubmissionStatus.FAILED)


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
            assert processing_started.wait(timeout=5), "Worker did not start processing within 5 seconds"

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

    def test_concurrent_enqueue_and_shutdown_no_stranded_items(self):
        """Items enqueued concurrently with shutdown are either processed or rejected."""
        processed: list[str] = []
        lock = threading.Lock()

        def tracking_processor(item: SubmissionItem) -> None:
            with lock:
                processed.append(item.file_path)

        # Run multiple iterations to increase the chance of exposing interleavings.
        # The lock-based fix is deterministic, so 20 iterations is sufficient to
        # exercise both orderings (enqueue-before-shutdown, shutdown-before-enqueue).
        for _ in range(20):
            manager = SubmissionManager(processor=tracking_processor)
            processed.clear()
            enqueued_items: list[SubmissionItem] = []
            errors: list[RuntimeError] = []

            # Enqueue one item to start the worker
            first = manager.enqueue(pr_id=1, file_path="first.ts", outcome="approve", summary="s")
            enqueued_items.append(first)

            ready = threading.Event()

            def enqueue_task() -> None:
                ready.wait(timeout=5)
                try:
                    item = manager.enqueue(pr_id=1, file_path="concurrent.ts", outcome="approve", summary="s")
                    enqueued_items.append(item)
                except RuntimeError as exc:
                    errors.append(exc)

            def shutdown_task() -> None:
                ready.wait(timeout=5)
                manager.shutdown(wait=True)

            t_enqueue = threading.Thread(target=enqueue_task)
            t_shutdown = threading.Thread(target=shutdown_task)
            t_enqueue.start()
            t_shutdown.start()

            # Release both threads simultaneously to maximise interleaving
            ready.set()
            t_enqueue.join(timeout=5)
            t_shutdown.join(timeout=5)

            # Verify threads completed (no deadlock)
            assert not t_enqueue.is_alive(), "enqueue thread hung"
            assert not t_shutdown.is_alive(), "shutdown thread hung"

            # The concurrent enqueue was either accepted or rejected
            assert len(enqueued_items) + len(errors) >= 2  # first + concurrent outcome

            # Every successfully enqueued item must have been processed
            for item in enqueued_items:
                assert item.status in (
                    SubmissionStatus.SUCCEEDED,
                    SubmissionStatus.FAILED,
                ), f"Item {item.file_path} stranded with status={item.status}"

    def test_shutdown_wait_starts_worker_when_not_yet_started(self):
        """shutdown(wait=True) must drain and join even if the worker hasn't started yet."""
        manager = SubmissionManager()
        # Directly put an item and sentinel on the queue WITHOUT starting the worker,
        # simulating the interleaving where enqueue() put the item but hasn't called
        # _ensure_worker_started() yet when shutdown(wait=True) runs.
        item = SubmissionItem(
            id="test-id",
            pr_id=1,
            file_path="file.ts",
            outcome="approve",
            summary="ok",
        )
        manager._items[item.id] = item
        manager._queue.put(item)
        # Worker is still None at this point
        assert manager._worker is None

        # shutdown(wait=True) should start the worker, drain the queue, and join
        manager.shutdown(wait=True)

        assert manager._worker is not None
        assert not manager._worker.is_alive()
        assert item.status == SubmissionStatus.SUCCEEDED

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
            start = time.monotonic()
            while manager._worker is None and time.monotonic() - start < 1.0:
                time.sleep(0.005)
            assert manager._worker is not None, "Worker thread was not started within timeout"
            assert manager._worker.daemon is True
        finally:
            manager.shutdown(wait=True)

    def test_transient_error_retried_and_succeeds(self):
        """Processor raises TransientSubmissionError on first 2 attempts, succeeds on 3rd."""
        call_count = 0
        done = threading.Event()

        def flaky_processor(item: SubmissionItem) -> None:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TransientSubmissionError(f"transient error #{call_count}")
            done.set()

        manager = SubmissionManager(processor=flaky_processor, max_retries=3, backoff_base=0.01)
        item = manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")
        assert done.wait(timeout=10), "Processor did not succeed within timeout"
        manager.shutdown(wait=True)

        assert item.status == SubmissionStatus.SUCCEEDED
        assert item.attempts == 3
        assert call_count == 3

    def test_transient_error_exhausts_retries(self):
        """Processor always raises TransientSubmissionError — exhausts all retries."""

        def always_transient(item: SubmissionItem) -> None:
            raise TransientSubmissionError("always failing")

        manager = SubmissionManager(processor=always_transient, max_retries=2, backoff_base=0.01)
        item = manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")

        # Wait for the item to reach terminal state
        start = time.monotonic()
        while item.status not in _TERMINAL and time.monotonic() - start < 10:
            time.sleep(0.01)
        manager.shutdown(wait=True)

        assert item.status == SubmissionStatus.FAILED
        assert item.attempts == 3  # 1 initial + 2 retries
        assert item.error_message == "always failing"

    def test_permanent_error_no_retry(self):
        """Processor raises ValueError — no retry, immediate failure."""

        def permanent_fail(item: SubmissionItem) -> None:
            raise ValueError("permanent error")

        manager = SubmissionManager(processor=permanent_fail, max_retries=3, backoff_base=0.01)
        try:
            item = manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")
        finally:
            manager.shutdown(wait=True)

        assert item.status == SubmissionStatus.FAILED
        assert item.attempts == 1
        assert item.error_message == "permanent error"

    def test_transient_then_permanent_error(self):
        """Transient on attempt 1, permanent on attempt 2."""
        call_count = 0

        def mixed_processor(item: SubmissionItem) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TransientSubmissionError("transient")
            raise ValueError("permanent")

        manager = SubmissionManager(processor=mixed_processor, max_retries=3, backoff_base=0.01)
        item = manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")

        # Wait for the item to reach terminal state
        start = time.monotonic()
        while item.status not in _TERMINAL and time.monotonic() - start < 10:
            time.sleep(0.01)
        manager.shutdown(wait=True)

        assert item.status == SubmissionStatus.FAILED
        assert item.attempts == 2
        assert item.error_message == "permanent"

    def test_retrying_status_visible_during_backoff(self):
        """Use threading event to observe RETRYING status during backoff."""
        observed_retrying = threading.Event()

        def transient_once(item: SubmissionItem) -> None:
            if item.attempts == 1:
                raise TransientSubmissionError("transient")

        manager = SubmissionManager(processor=transient_once, max_retries=3, backoff_base=0.5)
        item = manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")

        # Poll for RETRYING status
        start = time.monotonic()
        while time.monotonic() - start < 5:
            if item.status == SubmissionStatus.RETRYING:
                observed_retrying.set()
                break
            time.sleep(0.005)

        # Wait for processing to complete
        start = time.monotonic()
        while item.status not in _TERMINAL and time.monotonic() - start < 10:
            time.sleep(0.01)
        manager.shutdown(wait=True)

        assert observed_retrying.is_set(), "RETRYING status was never observed"
        assert item.status == SubmissionStatus.SUCCEEDED

    def test_shutdown_interrupts_backoff(self):
        """Shutdown during backoff sleep completes promptly."""

        def always_transient(item: SubmissionItem) -> None:
            raise TransientSubmissionError("transient error")

        # Use large backoff so the worker is definitely sleeping when shutdown fires.
        # This proves that _shutdown_event.wait() returns immediately on shutdown.
        manager = SubmissionManager(processor=always_transient, max_retries=10, backoff_base=100.0)
        item = manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")

        # Wait a bit for the first attempt to fail and enter backoff
        time.sleep(0.2)

        start = time.monotonic()
        manager.shutdown(wait=True)
        elapsed = time.monotonic() - start

        assert elapsed < 2.0, f"Shutdown took too long: {elapsed:.2f}s"
        assert item.status == SubmissionStatus.FAILED
        assert item.error_message == "transient error"

    def test_failure_report_after_shutdown(self):
        """shutdown(wait=True) returns FailureReport with correct entries."""

        def failing_processor(item: SubmissionItem) -> None:
            if item.file_path == "fail.ts":
                raise ValueError("fail reason")

        manager = SubmissionManager(processor=failing_processor, max_retries=0, backoff_base=0.01)
        manager.enqueue(pr_id=1, file_path="pass.ts", outcome="approve", summary="ok")
        manager.enqueue(pr_id=1, file_path="fail.ts", outcome="approve", summary="ok")

        report = manager.shutdown(wait=True)

        assert report is not None
        assert isinstance(report, FailureReport)
        assert len(report.failed_items) == 1
        assert report.failed_items[0].file_path == "fail.ts"
        assert report.failed_items[0].last_error == "fail reason"

    def test_failure_report_none_when_all_succeed(self):
        """All items succeed — shutdown returns None."""
        manager = SubmissionManager()
        manager.enqueue(pr_id=1, file_path="a.ts", outcome="approve", summary="ok")
        manager.enqueue(pr_id=1, file_path="b.ts", outcome="approve", summary="ok")

        report = manager.shutdown(wait=True)
        assert report is None

    def test_get_failure_report_on_demand(self):
        """get_failure_report() returns current failures after processing."""

        def fail_all(item: SubmissionItem) -> None:
            raise ValueError("error")

        manager = SubmissionManager(processor=fail_all, max_retries=0)
        manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")
        manager.shutdown(wait=True)

        report = manager.get_failure_report()
        assert report is not None
        assert len(report.failed_items) == 1

    def test_get_failure_report_none_when_no_failures(self):
        """get_failure_report() returns None when no items have failed."""
        manager = SubmissionManager()
        manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")
        manager.shutdown(wait=True)

        report = manager.get_failure_report()
        assert report is None

    def test_max_retries_zero_no_retry(self):
        """max_retries=0 — transient error fails immediately."""

        def transient_fail(item: SubmissionItem) -> None:
            raise TransientSubmissionError("transient")

        manager = SubmissionManager(processor=transient_fail, max_retries=0, backoff_base=0.01)
        item = manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")
        manager.shutdown(wait=True)

        assert item.status == SubmissionStatus.FAILED
        assert item.attempts == 1
        assert item.error_message == "transient"

    def test_invalid_max_retries_raises(self):
        """max_retries=-1 raises ValueError."""
        with pytest.raises(ValueError, match="max_retries must be >= 0"):
            SubmissionManager(max_retries=-1)

    def test_invalid_backoff_base_zero_raises(self):
        """backoff_base=0 raises ValueError."""
        with pytest.raises(ValueError, match="backoff_base must be > 0"):
            SubmissionManager(backoff_base=0)

    def test_invalid_backoff_base_negative_raises(self):
        """backoff_base=-1 raises ValueError."""
        with pytest.raises(ValueError, match="backoff_base must be > 0"):
            SubmissionManager(backoff_base=-1)

    def test_create_submission_manager_forwards_retry_params(self):
        """Factory forwards max_retries and backoff_base."""

        def transient_fail(item: SubmissionItem) -> None:
            raise TransientSubmissionError("transient")

        manager = create_submission_manager(processor=transient_fail, max_retries=1, backoff_base=0.01)
        item = manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")

        # Wait for the item to reach terminal state
        start = time.monotonic()
        while item.status not in _TERMINAL and time.monotonic() - start < 10:
            time.sleep(0.01)
        manager.shutdown(wait=True)

        assert item.status == SubmissionStatus.FAILED
        assert item.attempts == 2  # 1 initial + 1 retry (max_retries=1)

    def test_mixed_items_independent_retry(self):
        """3 items: transient-fail, succeed, permanent-fail — independent handling."""
        call_counts: dict[str, int] = {}

        def mixed_processor(item: SubmissionItem) -> None:
            call_counts[item.file_path] = call_counts.get(item.file_path, 0) + 1
            if item.file_path == "transient.ts":
                raise TransientSubmissionError("transient")
            if item.file_path == "permanent.ts":
                raise ValueError("permanent")

        manager = SubmissionManager(processor=mixed_processor, max_retries=2, backoff_base=0.01)
        item1 = manager.enqueue(pr_id=1, file_path="transient.ts", outcome="approve", summary="ok")
        item2 = manager.enqueue(pr_id=1, file_path="success.ts", outcome="approve", summary="ok")
        item3 = manager.enqueue(pr_id=1, file_path="permanent.ts", outcome="approve", summary="ok")

        # Wait for all items to reach terminal state
        items = [item1, item2, item3]
        start = time.monotonic()
        while time.monotonic() - start < 15:
            if all(i.status in _TERMINAL for i in items):
                break
            time.sleep(0.01)
        manager.shutdown(wait=True)

        assert item1.status == SubmissionStatus.FAILED
        assert item1.attempts == 3  # exhausted retries
        assert item2.status == SubmissionStatus.SUCCEEDED
        assert item2.attempts == 1
        assert item3.status == SubmissionStatus.FAILED
        assert item3.attempts == 1  # permanent = no retry

    def test_shutdown_wait_false_returns_none(self):
        """shutdown(wait=False) always returns None."""
        manager = SubmissionManager()
        manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")
        result = manager.shutdown(wait=False)
        assert result is None
        # Clean up
        manager.shutdown(wait=True)
