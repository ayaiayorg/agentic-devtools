"""Tests for sync_submission_pending_with_tasks function."""

import json
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.file_review_commands import sync_submission_pending_with_tasks
from agentic_devtools.task_state import TaskStatus


class TestSyncSubmissionPendingWithTasks:
    """Tests for sync_submission_pending_with_tasks function."""

    def test_updates_entry_to_completed_when_task_succeeds(self, tmp_path):
        """Should move entry to completed list when background task succeeded."""
        queue_data = {
            "pending": [
                {
                    "path": "src/a.ts",
                    "status": "submission-pending",
                    "taskId": "task-123",
                }
            ],
            "completed": [],
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        mock_task = MagicMock()
        mock_task.status = TaskStatus.COMPLETED
        mock_task.exit_code = 0
        mock_task.error_message = None

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            with patch(
                "agentic_devtools.task_state.get_task_by_id",
                return_value=mock_task,
            ):
                sync_submission_pending_with_tasks(pull_request_id=42)

        updated = json.loads(queue_file.read_text())
        assert len(updated["completed"]) == 1

    def test_does_nothing_when_no_queue_file(self, tmp_path):
        """Should not raise when the queue file does not exist."""
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=tmp_path / "nonexistent.json",
        ):
            # Should complete without raising
            sync_submission_pending_with_tasks(pull_request_id=42)
