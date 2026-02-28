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

    def test_calls_trigger_in_progress_when_file_pending(self, tmp_path):
        """Should call trigger_in_progress_for_file when there is a pending file."""
        queue_data = {
            "pending": [{"path": "src/app.py", "status": "pending"}],
            "completed": [],
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            with patch("agentic_devtools.cli.azure_devops.file_review_commands.sync_submission_pending_with_tasks"):
                with patch(
                    "agentic_devtools.cli.azure_devops.file_review_commands.trigger_in_progress_for_file"
                ) as mock_trigger:
                    with patch("agentic_devtools.cli.azure_devops.file_review_commands.is_dry_run", return_value=False):
                        print_next_file_prompt(pull_request_id=42)

        mock_trigger.assert_called_once_with(
            pull_request_id=42,
            file_path="src/app.py",
            dry_run=False,
        )

    def test_does_not_call_trigger_in_progress_when_all_complete(self, tmp_path):
        """Should not call trigger_in_progress_for_file when all files are reviewed."""
        queue_data = {
            "pending": [],
            "completed": [{"path": "src/app.py"}],
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            with patch("agentic_devtools.cli.azure_devops.file_review_commands.sync_submission_pending_with_tasks"):
                with patch(
                    "agentic_devtools.cli.azure_devops.file_review_commands.trigger_in_progress_for_file"
                ) as mock_trigger:
                    print_next_file_prompt(pull_request_id=42)

        mock_trigger.assert_not_called()

    def test_trigger_exception_does_not_crash(self, tmp_path, capsys):
        """Should print a warning but not crash when trigger_in_progress_for_file raises."""
        queue_data = {
            "pending": [{"path": "src/app.py", "status": "pending"}],
            "completed": [],
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            with patch("agentic_devtools.cli.azure_devops.file_review_commands.sync_submission_pending_with_tasks"):
                with patch(
                    "agentic_devtools.cli.azure_devops.file_review_commands.trigger_in_progress_for_file",
                    side_effect=RuntimeError("boom"),
                ):
                    with patch("agentic_devtools.cli.azure_devops.file_review_commands.is_dry_run", return_value=False):
                        # Should not raise
                        print_next_file_prompt(pull_request_id=42)

        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "in-progress" in captured.err
