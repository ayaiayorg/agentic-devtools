"""Tests for agentic_devtools.submission_manager.create_submission_manager."""

import json

from agentic_devtools.submission_manager import (
    SubmissionItem,
    SubmissionManager,
    SubmissionStatus,
    create_submission_manager,
)


class TestCreateSubmissionManager:
    """Tests for the create_submission_manager factory function."""

    def test_returns_submission_manager_instance(self):
        """Factory returns a SubmissionManager instance."""
        manager = create_submission_manager()
        try:
            assert isinstance(manager, SubmissionManager)
        finally:
            manager.shutdown(wait=True)

    def test_with_custom_processor(self):
        """Factory accepts a custom processor callable."""
        received: list[SubmissionItem] = []

        def custom_proc(item: SubmissionItem) -> None:
            received.append(item)

        manager = create_submission_manager(processor=custom_proc)
        try:
            item = manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")
        finally:
            manager.shutdown(wait=True)

        assert len(received) == 1
        assert received[0].id == item.id

    def test_default_processor_marks_succeeded(self):
        """Factory with no processor uses default no-op, items succeed."""
        manager = create_submission_manager()
        try:
            item = manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")
        finally:
            manager.shutdown(wait=True)

        assert item.status == SubmissionStatus.SUCCEEDED

    def test_forwards_persistence_path(self, tmp_path):
        """Factory forwards persistence_path to SubmissionManager."""
        persist_file = tmp_path / "queue.json"
        manager = create_submission_manager(persistence_path=persist_file)
        try:
            manager.enqueue(pr_id=1, file_path="file.ts", outcome="approve", summary="ok")
        finally:
            manager.shutdown(wait=True)

        assert persist_file.exists()
        data = json.loads(persist_file.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert len(data["items"]) == 1
