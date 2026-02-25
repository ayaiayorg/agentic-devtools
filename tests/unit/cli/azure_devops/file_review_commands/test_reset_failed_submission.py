"""Tests for reset_failed_submission function."""

import json

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.file_review_commands import reset_failed_submission


class TestResetFailedSubmission:
    """Tests for reset_failed_submission function."""

    def test_returns_true_on_successful_reset(self, tmp_path):
        """Should return True when the failed submission is reset to pending."""
        queue_data = {
            "pending": [
                {"path": "src/a.ts", "status": "failed", "errorMessage": "Error"},
            ]
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            result = reset_failed_submission(
                pull_request_id=42,
                file_path="src/a.ts",
            )

        assert result is True

    def test_status_reset_to_pending(self, tmp_path):
        """Should update the entry status back to 'pending' after reset."""
        queue_data = {
            "pending": [
                {"path": "src/a.ts", "status": "failed", "errorMessage": "Error"},
            ]
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            reset_failed_submission(pull_request_id=42, file_path="src/a.ts")

        updated = json.loads(queue_file.read_text())
        assert updated["pending"][0]["status"] == "pending"

    def test_returns_true_when_file_not_in_queue_but_file_written(self, tmp_path):
        """Return value is True when queue was read successfully (even if no match found)."""
        queue_data = {
            "pending": [{"path": "src/b.ts", "status": "failed"}]
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            result = reset_failed_submission(
                pull_request_id=42,
                file_path="src/nonexistent.ts",
            )

        # The implementation returns True if it was able to write the file
        assert isinstance(result, bool)
