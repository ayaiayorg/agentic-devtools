"""Tests for print_next_file_prompt function."""

import json
from unittest.mock import patch

from agentic_devtools.cli.azure_devops.file_review_commands import print_next_file_prompt


class TestPrintNextFilePrompt:
    """Tests for print_next_file_prompt function."""

    def test_prints_no_pending_message_when_all_done(self, tmp_path, capsys):
        """Should print a completion message when all files are reviewed."""
        queue_data = {
            "pending": [],
            "completed": [{"path": "src/a.ts"}],
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            with patch("agentic_devtools.cli.azure_devops.file_review_commands.sync_submission_pending_with_tasks"):
                print_next_file_prompt(pull_request_id=42)

        captured = capsys.readouterr()
        assert captured.out != "" or captured.err != ""

    def test_calls_sync_submission_pending_with_tasks(self, tmp_path):
        """Should call sync_submission_pending_with_tasks to refresh task status."""
        queue_data = {
            "pending": [],
            "completed": [{"path": "src/a.ts"}],
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.sync_submission_pending_with_tasks"
            ) as mock_sync:
                print_next_file_prompt(pull_request_id=42)

        mock_sync.assert_called_once_with(42)
