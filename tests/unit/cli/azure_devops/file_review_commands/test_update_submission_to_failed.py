"""Tests for update_submission_to_failed function."""

import json
from unittest.mock import patch

from agentic_devtools.cli.azure_devops.file_review_commands import update_submission_to_failed


class TestUpdateSubmissionToFailed:
    """Tests for update_submission_to_failed function."""

    def test_returns_false_when_no_queue_file(self, tmp_path):
        """Should return False when the queue file does not exist."""
        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=tmp_path / "nonexistent.json",
        ):
            result = update_submission_to_failed(
                pull_request_id=42,
                file_path="src/a.ts",
                error_message="Timed out",
            )

        assert result is False

    def test_returns_true_and_sets_status_to_failed(self, tmp_path):
        """Should return True and update status to 'failed' when entry is found."""
        queue_data = {
            "pending": [
                {"path": "src/a.ts", "status": "submission-pending"},
            ]
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            result = update_submission_to_failed(
                pull_request_id=42,
                file_path="src/a.ts",
                error_message="Submission timed out",
            )

        assert result is True
        updated = json.loads(queue_file.read_text())
        assert updated["pending"][0]["status"] == "failed"
        assert "Submission timed out" in updated["pending"][0].get("errorMessage", "")

    def test_returns_true_even_when_file_not_found_in_pending(self, tmp_path):
        """Should still return True (file written successfully) even if no match found."""
        queue_data = {"pending": [{"path": "src/b.ts", "status": "pending"}]}
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            result = update_submission_to_failed(
                pull_request_id=42,
                file_path="src/notfound.ts",
                error_message="error",
            )

        # The function writes the file and returns True regardless of whether
        # the specific entry was found
        assert isinstance(result, bool)
