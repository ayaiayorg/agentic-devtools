"""Tests for _update_queue_after_review function."""

import json
from unittest.mock import patch

from agentic_devtools.cli.azure_devops.file_review_commands import _update_queue_after_review


class TestUpdateQueueAfterReview:
    """Tests for _update_queue_after_review function."""

    def test_moves_file_from_pending_to_completed(self, tmp_path):
        """Should move the matching file from pending to completed."""
        queue_data = {
            "pending": [
                {"path": "/src/app.ts", "status": "pending"},
                {"path": "/src/utils.ts", "status": "pending"},
            ],
            "completed": [],
        }
        queue_path = tmp_path / "queue.json"
        queue_path.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            pending, completed = _update_queue_after_review(
                pull_request_id=42,
                file_path="/src/app.ts",
                outcome="Approve",
            )

        assert pending == 1
        assert completed == 1

        with open(queue_path, encoding="utf-8") as f:
            updated = json.load(f)

        assert len(updated["pending"]) == 1
        assert len(updated["completed"]) == 1
        assert updated["completed"][0]["path"] == "/src/app.ts"
        assert updated["completed"][0]["status"] == "completed"
        assert updated["completed"][0]["outcome"] == "Approve"
        assert "completedUtc" in updated["completed"][0]

    def test_returns_zero_counts_when_queue_missing(self, tmp_path):
        """Should return (0, 0) when queue file doesn't exist."""
        non_existent = tmp_path / "nonexistent" / "queue.json"

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=non_existent,
        ):
            pending, completed = _update_queue_after_review(
                pull_request_id=42,
                file_path="/src/app.ts",
                outcome="Approve",
            )

        assert pending == 0
        assert completed == 0

    def test_dry_run_does_not_write(self, tmp_path):
        """Should not modify the queue file when dry_run is True."""
        queue_data = {
            "pending": [{"path": "/src/app.ts", "status": "pending"}],
            "completed": [],
        }
        queue_path = tmp_path / "queue.json"
        queue_path.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            pending, completed = _update_queue_after_review(
                pull_request_id=42,
                file_path="/src/app.ts",
                outcome="Approve",
                dry_run=True,
            )

        assert pending == 0
        assert completed == 1

        # File should not be modified
        with open(queue_path, encoding="utf-8") as f:
            unchanged = json.load(f)
        assert len(unchanged["pending"]) == 1

    def test_cleans_up_submission_tracking_fields(self, tmp_path):
        """Should remove taskId, submittedUtc, failedUtc, errorMessage from the entry."""
        queue_data = {
            "pending": [
                {
                    "path": "/src/app.ts",
                    "status": "submission-pending",
                    "taskId": "task-123",
                    "submittedUtc": "2024-01-01T12:00:00Z",
                    "failedUtc": "2024-01-01T12:01:00Z",
                    "errorMessage": "Previous error",
                },
            ],
            "completed": [],
        }
        queue_path = tmp_path / "queue.json"
        queue_path.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            _update_queue_after_review(
                pull_request_id=42,
                file_path="/src/app.ts",
                outcome="Changes",
            )

        with open(queue_path, encoding="utf-8") as f:
            updated = json.load(f)

        entry = updated["completed"][0]
        assert "taskId" not in entry
        assert "submittedUtc" not in entry
        assert "failedUtc" not in entry
        assert "errorMessage" not in entry
        assert entry["status"] == "completed"
        assert entry["outcome"] == "Changes"

    def test_idempotent_when_file_already_completed(self, tmp_path):
        """Should silently return current counts when the file is already in completed.

        This happens when the async wrapper calls _update_queue_after_review to
        advance the queue immediately, and then the background task's sync
        function calls it again after completing.
        """
        queue_data = {
            "pending": [{"path": "/src/utils.ts", "status": "pending"}],
            "completed": [
                {
                    "path": "/src/app.ts",
                    "status": "completed",
                    "outcome": "Approve",
                    "completedUtc": "2024-01-01T12:00:00Z",
                },
            ],
        }
        queue_path = tmp_path / "queue.json"
        queue_path.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            pending, completed = _update_queue_after_review(
                pull_request_id=42,
                file_path="/src/app.ts",
                outcome="Approve",
            )

        # Should return current counts without error
        assert pending == 1
        assert completed == 1

        # Queue file should be unchanged
        with open(queue_path, encoding="utf-8") as f:
            unchanged = json.load(f)
        assert len(unchanged["pending"]) == 1
        assert len(unchanged["completed"]) == 1
