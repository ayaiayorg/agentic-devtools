"""Tests for get_failed_submissions function."""

import json
from unittest.mock import patch

from agentic_devtools.cli.azure_devops.file_review_commands import get_failed_submissions


class TestGetFailedSubmissions:
    """Tests for get_failed_submissions function."""

    def test_returns_empty_list_when_no_queue_file(self, tmp_path):
        """Should return empty list when the queue file does not exist."""
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=tmp_path / "nonexistent-queue.json",
        ):
            result = get_failed_submissions(pull_request_id=42)

        assert result == []

    def test_returns_failed_entries(self, tmp_path):
        """Should return entries where status is 'failed'."""
        queue_data = {
            "pending": [
                {"path": "src/a.ts", "status": "failed", "errorMessage": "Submission error"},
                {"path": "src/b.ts", "status": "pending"},
            ]
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            result = get_failed_submissions(pull_request_id=42)

        assert len(result) == 1
        assert result[0]["path"] == "src/a.ts"

    def test_returns_empty_list_when_no_failed_entries(self, tmp_path):
        """Should return empty list when all queue entries are non-failed."""
        queue_data = {
            "pending": [
                {"path": "src/c.ts", "status": "pending"},
            ]
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            result = get_failed_submissions(pull_request_id=42)

        assert result == []
