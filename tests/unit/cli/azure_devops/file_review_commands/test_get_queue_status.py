"""Tests for get_queue_status function."""

import json
from unittest.mock import patch

from agentic_devtools.cli.azure_devops.file_review_commands import get_queue_status


class TestGetQueueStatus:
    """Tests for get_queue_status function."""

    def test_returns_default_status_when_no_queue_file(self, tmp_path):
        """Should return zeroed-out status dict when queue file does not exist."""
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=tmp_path / "nonexistent.json",
        ):
            result = get_queue_status(pull_request_id=42)

        assert result["pull_request_id"] == 42
        assert result["total_count"] == 0
        assert result["all_complete"] is False

    def test_counts_completed_files(self, tmp_path):
        """Should count files in the completed list correctly."""
        queue_data = {
            "pending": [{"path": "src/b.ts", "status": "pending"}],
            "completed": [{"path": "src/a.ts"}],
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            result = get_queue_status(pull_request_id=42)

        assert result["completed_count"] == 1
        assert result["total_count"] == 2

    def test_marks_all_complete_when_all_files_reviewed(self, tmp_path):
        """Should set all_complete=True when every file is in completed list."""
        queue_data = {
            "pending": [],
            "completed": [
                {"path": "src/a.ts"},
                {"path": "src/b.ts"},
            ],
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            result = get_queue_status(pull_request_id=42)

        assert result["all_complete"] is True
