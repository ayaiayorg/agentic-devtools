"""
Tests for file review queue management functions.

These tests cover the queue management functions in file_review_commands.py
that handle queue status tracking.
"""

import json
from unittest.mock import patch

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


class TestGetQueueStatus:
    """Tests for get_queue_status function."""

    def test_returns_correct_counts(self, temp_queue_dir):
        """Should return accurate queue status counts."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            get_queue_status,
        )

        queue_data = {
            "pending": [
                {"path": "/src/pending1.ts", "status": "pending"},
                {"path": "/src/pending2.ts", "status": "pending"},
            ],
            "completed": [
                {"path": "/src/done.ts", "status": "completed"},
            ],
        }

        queue_path = temp_queue_dir / "queue.json"
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f)

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            status = get_queue_status(pull_request_id=12345)

        assert status["pending_count"] == 2
        assert status["completed_count"] == 1
        assert status["total_count"] == 3
        assert status["all_complete"] is False
        assert status["current_file"] == "/src/pending1.ts"
        assert "submission_pending_count" not in status
        assert "failed_count" not in status

    def test_all_complete_when_no_pending(self, temp_queue_dir):
        """Should mark all_complete when no pending files remain."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
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
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_path,
        ):
            status = get_queue_status(pull_request_id=12345)

        assert status["all_complete"] is True
        assert status["current_file"] is None

    def test_returns_empty_status_for_missing_queue(self, tmp_path):
        """Should return empty status when queue doesn't exist."""
        from agentic_devtools.cli.azure_devops.file_review_commands import (
            get_queue_status,
        )

        non_existent = tmp_path / "nonexistent" / "queue.json"

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=non_existent,
        ):
            status = get_queue_status(pull_request_id=12345)

        assert status["pending_count"] == 0
        assert status["completed_count"] == 0
        assert status["all_complete"] is False
