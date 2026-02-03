"""
Tests for file review queue management functions.

These tests cover the queue management functions in file_review_commands.py
that handle submission tracking, failure handling, and workflow continuation.
"""

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_queue_dir(tmp_path):
    """Create a temporary directory structure for queue files."""
    prompts_dir = tmp_path / "temp" / "pull-request-review" / "prompts" / "12345"
    prompts_dir.mkdir(parents=True)
    return prompts_dir


@pytest.fixture
def sample_queue_data():
    """Create sample queue data with pending and completed entries."""
    return {
        "pull_request_id": 12345,
        "lastUpdatedUtc": "2024-01-01T12:00:00Z",
        "pending": [
            {"path": "/src/app.ts", "status": "pending"},
            {"path": "/src/utils.ts", "status": "pending"},
            {"path": "/src/test.ts", "status": "submission-pending", "taskId": "task-123"},
        ],
        "completed": [
            {"path": "/src/done.ts", "status": "completed", "outcome": "Approve"},
        ],
    }


@pytest.fixture
def queue_file(temp_queue_dir, sample_queue_data):
    """Create a queue.json file with sample data."""
    queue_path = temp_queue_dir / "queue.json"
    with open(queue_path, "w", encoding="utf-8") as f:
        json.dump(sample_queue_data, f)
    return queue_path


class TestMarkFileAsSubmissionPending:
    """Tests for mark_file_as_submission_pending function."""

    def test_marks_file_as_submission_pending(self, temp_queue_dir, queue_file):
        """Should update file status to submission-pending."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            mark_file_as_submission_pending,
        )

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            result = mark_file_as_submission_pending(
                pull_request_id=12345,
                file_path="/src/app.ts",
                task_id="task-456",
                outcome="Approve",
            )

        assert result is True

        # Verify the file was updated
        with open(queue_file, encoding="utf-8") as f:
            data = json.load(f)

        pending = data["pending"]
        app_entry = next(e for e in pending if e["path"] == "/src/app.ts")
        assert app_entry["status"] == "submission-pending"
        assert app_entry["taskId"] == "task-456"
        assert app_entry["outcome"] == "Approve"
        assert "submittedUtc" in app_entry

    def test_returns_false_when_queue_not_found(self, tmp_path):
        """Should return False when queue file doesn't exist."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            mark_file_as_submission_pending,
        )

        non_existent = tmp_path / "nonexistent" / "queue.json"

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=non_existent,
        ):
            result = mark_file_as_submission_pending(
                pull_request_id=12345,
                file_path="/src/app.ts",
                task_id="task-456",
                outcome="Approve",
            )

        assert result is False

    def test_returns_false_for_file_not_in_queue(self, temp_queue_dir, queue_file):
        """Should return False when file is not in pending queue."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            mark_file_as_submission_pending,
        )

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            result = mark_file_as_submission_pending(
                pull_request_id=12345,
                file_path="/src/nonexistent.ts",
                task_id="task-456",
                outcome="Approve",
            )

        assert result is False

    def test_handles_invalid_json(self, temp_queue_dir):
        """Should return False for invalid JSON."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            mark_file_as_submission_pending,
        )

        queue_path = temp_queue_dir / "queue.json"
        with open(queue_path, "w", encoding="utf-8") as f:
            f.write("not valid json")

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            result = mark_file_as_submission_pending(
                pull_request_id=12345,
                file_path="/src/app.ts",
                task_id="task-456",
                outcome="Approve",
            )

        assert result is False

    def test_cleans_up_failure_fields(self, temp_queue_dir):
        """Should remove failure fields when marking as submission-pending."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            mark_file_as_submission_pending,
        )

        queue_data = {
            "pending": [
                {
                    "path": "/src/app.ts",
                    "status": "failed",
                    "failedUtc": "2024-01-01T12:00:00Z",
                    "errorMessage": "Previous error",
                },
            ],
            "completed": [],
        }

        queue_path = temp_queue_dir / "queue.json"
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            result = mark_file_as_submission_pending(
                pull_request_id=12345,
                file_path="/src/app.ts",
                task_id="task-456",
                outcome="Approve",
            )

        assert result is True

        with open(queue_path, encoding="utf-8") as f:
            data = json.load(f)

        app_entry = data["pending"][0]
        assert "failedUtc" not in app_entry
        assert "errorMessage" not in app_entry


class TestUpdateSubmissionToCompleted:
    """Tests for update_submission_to_completed function."""

    def test_moves_file_to_completed(self, temp_queue_dir, queue_file):
        """Should move file from pending to completed."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            update_submission_to_completed,
        )

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            result = update_submission_to_completed(
                pull_request_id=12345,
                file_path="/src/app.ts",
            )

        assert result is True

        with open(queue_file, encoding="utf-8") as f:
            data = json.load(f)

        # File should be moved to completed
        pending_paths = [e["path"] for e in data["pending"]]
        completed_paths = [e["path"] for e in data["completed"]]

        assert "/src/app.ts" not in pending_paths
        assert "/src/app.ts" in completed_paths

        # Check completed entry has correct status
        completed_entry = next(e for e in data["completed"] if e["path"] == "/src/app.ts")
        assert completed_entry["status"] == "completed"
        assert "completedUtc" in completed_entry

    def test_returns_false_when_queue_not_found(self, tmp_path):
        """Should return False when queue file doesn't exist."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            update_submission_to_completed,
        )

        non_existent = tmp_path / "nonexistent" / "queue.json"

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=non_existent,
        ):
            result = update_submission_to_completed(
                pull_request_id=12345,
                file_path="/src/app.ts",
            )

        assert result is False

    def test_returns_false_for_file_not_in_queue(self, temp_queue_dir, queue_file):
        """Should return False when file is not found."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            update_submission_to_completed,
        )

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            result = update_submission_to_completed(
                pull_request_id=12345,
                file_path="/src/nonexistent.ts",
            )

        assert result is False


class TestUpdateSubmissionToFailed:
    """Tests for update_submission_to_failed function."""

    def test_marks_file_as_failed(self, temp_queue_dir, queue_file):
        """Should update file status to failed with error message."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            update_submission_to_failed,
        )

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            result = update_submission_to_failed(
                pull_request_id=12345,
                file_path="/src/app.ts",
                error_message="API error: 500",
            )

        assert result is True

        with open(queue_file, encoding="utf-8") as f:
            data = json.load(f)

        app_entry = next(e for e in data["pending"] if e["path"] == "/src/app.ts")
        assert app_entry["status"] == "failed"
        assert app_entry["errorMessage"] == "API error: 500"
        assert "failedUtc" in app_entry

    def test_returns_false_when_queue_not_found(self, tmp_path):
        """Should return False when queue file doesn't exist."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            update_submission_to_failed,
        )

        non_existent = tmp_path / "nonexistent" / "queue.json"

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=non_existent,
        ):
            result = update_submission_to_failed(
                pull_request_id=12345,
                file_path="/src/app.ts",
                error_message="Error",
            )

        assert result is False


class TestGetFailedSubmissions:
    """Tests for get_failed_submissions function."""

    def test_returns_failed_entries(self, temp_queue_dir):
        """Should return list of failed entries."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            get_failed_submissions,
        )

        queue_data = {
            "pending": [
                {"path": "/src/app.ts", "status": "pending"},
                {"path": "/src/failed1.ts", "status": "failed", "errorMessage": "Error 1"},
                {"path": "/src/failed2.ts", "status": "failed", "errorMessage": "Error 2"},
            ],
            "completed": [],
        }

        queue_path = temp_queue_dir / "queue.json"
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            result = get_failed_submissions(pull_request_id=12345)

        assert len(result) == 2
        paths = [e["path"] for e in result]
        assert "/src/failed1.ts" in paths
        assert "/src/failed2.ts" in paths

    def test_returns_empty_for_no_failures(self, temp_queue_dir, queue_file):
        """Should return empty list when no failures."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            get_failed_submissions,
        )

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            result = get_failed_submissions(pull_request_id=12345)

        assert result == []

    def test_returns_empty_when_queue_not_found(self, tmp_path):
        """Should return empty list when queue doesn't exist."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            get_failed_submissions,
        )

        non_existent = tmp_path / "nonexistent" / "queue.json"

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=non_existent,
        ):
            result = get_failed_submissions(pull_request_id=12345)

        assert result == []


class TestResetFailedSubmission:
    """Tests for reset_failed_submission function."""

    def test_resets_failed_to_pending(self, temp_queue_dir):
        """Should reset failed entry back to pending status."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            reset_failed_submission,
        )

        queue_data = {
            "pending": [
                {
                    "path": "/src/failed.ts",
                    "status": "failed",
                    "taskId": "old-task",
                    "submittedUtc": "2024-01-01T12:00:00Z",
                    "failedUtc": "2024-01-01T12:01:00Z",
                    "errorMessage": "Error",
                    "outcome": "Approve",
                },
            ],
            "completed": [],
        }

        queue_path = temp_queue_dir / "queue.json"
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            result = reset_failed_submission(
                pull_request_id=12345,
                file_path="/src/failed.ts",
            )

        assert result is True

        with open(queue_path, encoding="utf-8") as f:
            data = json.load(f)

        entry = data["pending"][0]
        assert entry["status"] == "pending"
        assert "taskId" not in entry
        assert "submittedUtc" not in entry
        assert "failedUtc" not in entry
        assert "errorMessage" not in entry
        assert "outcome" not in entry

    def test_does_not_reset_non_failed_entry(self, temp_queue_dir, queue_file):
        """Should not reset entries that aren't failed."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            reset_failed_submission,
        )

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            result = reset_failed_submission(
                pull_request_id=12345,
                file_path="/src/app.ts",  # This has status "pending", not "failed"
            )

        # Should return True but not change the status (already pending)
        assert result is True


class TestGetQueueStatus:
    """Tests for get_queue_status function."""

    def test_returns_correct_counts(self, temp_queue_dir):
        """Should return accurate queue status counts."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            get_queue_status,
        )

        queue_data = {
            "pending": [
                {"path": "/src/pending1.ts", "status": "pending"},
                {"path": "/src/pending2.ts", "status": "pending"},
                {"path": "/src/submitting.ts", "status": "submission-pending"},
                {"path": "/src/failed.ts", "status": "failed"},
            ],
            "completed": [
                {"path": "/src/done.ts", "status": "completed"},
            ],
        }

        queue_path = temp_queue_dir / "queue.json"
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            status = get_queue_status(pull_request_id=12345)

        assert status["pending_count"] == 2
        assert status["submission_pending_count"] == 1
        assert status["failed_count"] == 1
        assert status["completed_count"] == 1
        assert status["total_count"] == 5
        assert status["all_complete"] is False
        assert status["current_file"] == "/src/pending1.ts"

    def test_all_complete_when_no_pending(self, temp_queue_dir):
        """Should mark all_complete when no pending files remain."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            get_queue_status,
        )

        queue_data = {
            "pending": [],
            "completed": [
                {"path": "/src/done.ts", "status": "completed"},
            ],
        }

        queue_path = temp_queue_dir / "queue.json"
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            status = get_queue_status(pull_request_id=12345)

        assert status["all_complete"] is True
        assert status["current_file"] is None

    def test_returns_empty_status_for_missing_queue(self, tmp_path):
        """Should return empty status when queue doesn't exist."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            get_queue_status,
        )

        non_existent = tmp_path / "nonexistent" / "queue.json"

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=non_existent,
        ):
            status = get_queue_status(pull_request_id=12345)

        assert status["pending_count"] == 0
        assert status["completed_count"] == 0
        assert status["all_complete"] is False


class TestSyncSubmissionPendingWithTasks:
    """Tests for sync_submission_pending_with_tasks function."""

    def test_marks_completed_when_task_completed(self, temp_queue_dir):
        """Should move entry to completed when task is completed."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            sync_submission_pending_with_tasks,
        )
        from agdt_ai_helpers.task_state import TaskStatus

        queue_data = {
            "pending": [
                {
                    "path": "/src/app.ts",
                    "status": "submission-pending",
                    "taskId": "completed-task",
                },
            ],
            "completed": [],
        }

        queue_path = temp_queue_dir / "queue.json"
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f)

        mock_task = MagicMock()
        mock_task.status = TaskStatus.COMPLETED

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            with patch(
                "agdt_ai_helpers.task_state.get_task_by_id",
                return_value=mock_task,
            ):
                sync_submission_pending_with_tasks(pull_request_id=12345)

        with open(queue_path, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data["pending"]) == 0
        assert len(data["completed"]) == 1
        assert data["completed"][0]["path"] == "/src/app.ts"
        assert data["completed"][0]["status"] == "completed"

    def test_marks_failed_when_task_failed(self, temp_queue_dir):
        """Should mark entry as failed when task failed."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            sync_submission_pending_with_tasks,
        )
        from agdt_ai_helpers.task_state import TaskStatus

        queue_data = {
            "pending": [
                {
                    "path": "/src/app.ts",
                    "status": "submission-pending",
                    "taskId": "failed-task",
                },
            ],
            "completed": [],
        }

        queue_path = temp_queue_dir / "queue.json"
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f)

        mock_task = MagicMock()
        mock_task.status = TaskStatus.FAILED
        mock_task.error_message = "API error"
        mock_task.exit_code = 1

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            with patch(
                "agdt_ai_helpers.task_state.get_task_by_id",
                return_value=mock_task,
            ):
                sync_submission_pending_with_tasks(pull_request_id=12345)

        with open(queue_path, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data["pending"]) == 1
        entry = data["pending"][0]
        assert entry["status"] == "failed"
        assert entry["errorMessage"] == "API error"

    def test_marks_failed_when_task_not_found(self, temp_queue_dir):
        """Should mark entry as failed when task is not found."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            sync_submission_pending_with_tasks,
        )

        queue_data = {
            "pending": [
                {
                    "path": "/src/app.ts",
                    "status": "submission-pending",
                    "taskId": "missing-task",
                },
            ],
            "completed": [],
        }

        queue_path = temp_queue_dir / "queue.json"
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            with patch(
                "agdt_ai_helpers.task_state.get_task_by_id",
                return_value=None,
            ):
                sync_submission_pending_with_tasks(pull_request_id=12345)

        with open(queue_path, encoding="utf-8") as f:
            data = json.load(f)

        entry = data["pending"][0]
        assert entry["status"] == "failed"
        assert "not found" in entry["errorMessage"].lower()

    def test_does_nothing_for_running_task(self, temp_queue_dir):
        """Should leave entry unchanged when task is still running."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            sync_submission_pending_with_tasks,
        )
        from agdt_ai_helpers.task_state import TaskStatus

        queue_data = {
            "pending": [
                {
                    "path": "/src/app.ts",
                    "status": "submission-pending",
                    "taskId": "running-task",
                },
            ],
            "completed": [],
        }

        queue_path = temp_queue_dir / "queue.json"
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f)

        mock_task = MagicMock()
        mock_task.status = TaskStatus.RUNNING

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            with patch(
                "agdt_ai_helpers.task_state.get_task_by_id",
                return_value=mock_task,
            ):
                sync_submission_pending_with_tasks(pull_request_id=12345)

        with open(queue_path, encoding="utf-8") as f:
            data = json.load(f)

        # Status should remain submission-pending
        assert data["pending"][0]["status"] == "submission-pending"


class TestUpdateQueueAfterReview:
    """Tests for _update_queue_after_review function."""

    def test_moves_file_from_pending_to_completed(self, temp_queue_dir, queue_file):
        """Should move reviewed file to completed."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            _update_queue_after_review,
        )

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            pending, completed = _update_queue_after_review(
                pull_request_id=12345,
                file_path="/src/app.ts",
                outcome="Approve",
                dry_run=False,
            )

        # Should have updated counts
        assert pending == 2  # Down from 3
        assert completed == 2  # Up from 1

        with open(queue_file, encoding="utf-8") as f:
            data = json.load(f)

        pending_paths = [e["path"] for e in data["pending"]]
        completed_paths = [e["path"] for e in data["completed"]]

        assert "/src/app.ts" not in pending_paths
        assert "/src/app.ts" in completed_paths

    def test_dry_run_does_not_modify_file(self, temp_queue_dir, queue_file):
        """Should not modify queue in dry run mode."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            _update_queue_after_review,
        )

        # Read original data
        with open(queue_file, encoding="utf-8") as f:
            original_data = json.load(f)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            pending, completed = _update_queue_after_review(
                pull_request_id=12345,
                file_path="/src/app.ts",
                outcome="Approve",
                dry_run=True,
            )

        # Counts should show expected values after move
        assert pending == 2
        assert completed == 2

        # But file should be unchanged
        with open(queue_file, encoding="utf-8") as f:
            actual_data = json.load(f)

        assert len(actual_data["pending"]) == len(original_data["pending"])

    def test_returns_zero_for_missing_queue(self, tmp_path):
        """Should return zeros when queue doesn't exist."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            _update_queue_after_review,
        )

        non_existent = tmp_path / "nonexistent" / "queue.json"

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=non_existent,
        ):
            pending, completed = _update_queue_after_review(
                pull_request_id=12345,
                file_path="/src/app.ts",
                outcome="Approve",
                dry_run=False,
            )

        assert pending == 0
        assert completed == 0


class TestTriggerWorkflowContinuation:
    """Tests for _trigger_workflow_continuation function."""

    def test_prints_continuation_for_pending_files(self, capsys):
        """Should print continuation message when files remain."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            _trigger_workflow_continuation,
        )

        _trigger_workflow_continuation(
            pull_request_id=12345,
            pending_count=5,
            completed_count=3,
        )

        captured = capsys.readouterr()
        assert "3 completed" in captured.out
        assert "5 remaining" in captured.out

    def test_prints_completion_message_when_all_reviewed(self, capsys):
        """Should print completion message when all files reviewed (no summary generation)."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            _trigger_workflow_continuation,
        )

        _trigger_workflow_continuation(
            pull_request_id=12345,
            pending_count=0,
            completed_count=10,
        )

        captured = capsys.readouterr()
        assert "ALL FILES REVIEWED" in captured.out
        assert "10" in captured.out
        # Should NOT generate summary directly - that's handled by task completion
        assert "Summary generation will be triggered automatically" in captured.out


class TestPrintNextFilePrompt:
    """Tests for print_next_file_prompt function."""

    def test_shows_failed_submissions_first(self, temp_queue_dir, capsys):
        """Should show failed submissions before next file."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            print_next_file_prompt,
        )

        queue_data = {
            "pending": [
                {"path": "/src/pending.ts", "status": "pending"},
                {"path": "/src/failed.ts", "status": "failed", "errorMessage": "API error", "outcome": "Approve"},
            ],
            "completed": [],
        }

        queue_path = temp_queue_dir / "queue.json"
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            print_next_file_prompt(pull_request_id=12345)

        captured = capsys.readouterr()
        assert "FAILED SUBMISSIONS" in captured.out
        assert "/src/failed.ts" in captured.out
        assert "API error" in captured.out

    def test_shows_all_complete_message(self, temp_queue_dir, capsys):
        """Should show completion message when all files done."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            print_next_file_prompt,
        )

        queue_data = {
            "pending": [],
            "completed": [
                {"path": "/src/done.ts", "status": "completed"},
            ],
        }

        queue_path = temp_queue_dir / "queue.json"
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            print_next_file_prompt(pull_request_id=12345)

        captured = capsys.readouterr()
        assert "ALL FILES REVIEWED" in captured.out

    def test_shows_next_file_when_pending(self, temp_queue_dir, capsys):
        """Should show queue status when files remain."""
        from agdt_ai_helpers.cli.azure_devops.file_review_commands import (
            print_next_file_prompt,
        )

        queue_data = {
            "pending": [
                {"path": "/src/next.ts", "status": "pending"},
            ],
            "completed": [],
        }

        queue_path = temp_queue_dir / "queue.json"
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f)

        with patch(
            "agdt_ai_helpers.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            with patch(
                "agdt_ai_helpers.task_state.get_task_by_id",
                return_value=None,
            ):
                print_next_file_prompt(pull_request_id=12345)

        captured = capsys.readouterr()
        assert "QUEUE STATUS" in captured.out
        assert "1 pending" in captured.out
        assert "Continue with the next file" in captured.out
