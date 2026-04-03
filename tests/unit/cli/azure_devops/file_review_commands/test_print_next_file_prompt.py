"""Tests for print_next_file_prompt function."""

import json
from unittest.mock import patch

from agentic_devtools.cli.azure_devops.file_review_commands import print_next_file_prompt

_AUTO_ADVANCE_PATCH = "agentic_devtools.cli.tasks.commands._try_advance_pr_review_to_decision"


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
            with patch(
                "agentic_devtools.cli.azure_devops.file_review_commands._complete_active_session",
            ):
                with patch(_AUTO_ADVANCE_PATCH, return_value=True):
                    print_next_file_prompt(pull_request_id=42)

        captured = capsys.readouterr()
        assert captured.out != "" or captured.err != ""

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
            with patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.trigger_in_progress_for_file"
            ) as mock_trigger:
                with patch(
                    "agentic_devtools.cli.azure_devops.file_review_commands._complete_active_session",
                ):
                    with patch(_AUTO_ADVANCE_PATCH, return_value=True):
                        print_next_file_prompt(pull_request_id=42)

        mock_trigger.assert_not_called()

    def test_shows_advance_workflow_when_all_complete(self, tmp_path, capsys):
        """Should show agdt-advance-workflow instructions when auto-advance returns False."""
        queue_data = {
            "pending": [],
            "completed": [{"path": "src/a.ts"}, {"path": "src/b.ts"}],
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.file_review_commands._complete_active_session",
            ):
                with patch(_AUTO_ADVANCE_PATCH, return_value=False):
                    print_next_file_prompt(pull_request_id=42)

        captured = capsys.readouterr()
        assert "READY FOR DECISION" in captured.out
        assert "agdt-advance-workflow" in captured.out
        assert "agdt-task-wait" not in captured.out

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

    def test_calls_complete_active_session_when_all_complete(self, tmp_path):
        """Should call _complete_active_session with the correct PR ID when all files are done."""
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
                "agentic_devtools.cli.azure_devops.file_review_commands._complete_active_session",
            ) as mock_complete:
                with patch("agentic_devtools.cli.azure_devops.file_review_commands.is_dry_run", return_value=False):
                    with patch(_AUTO_ADVANCE_PATCH, return_value=True):
                        print_next_file_prompt(pull_request_id=99)

        mock_complete.assert_called_once_with(99)

    def test_does_not_call_complete_active_session_when_files_pending(self, tmp_path):
        """Should not call _complete_active_session when files remain pending."""
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
            with patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.trigger_in_progress_for_file",
            ):
                with patch("agentic_devtools.cli.azure_devops.file_review_commands.is_dry_run", return_value=False):
                    with patch(
                        "agentic_devtools.cli.azure_devops.file_review_commands._complete_active_session",
                    ) as mock_complete:
                        print_next_file_prompt(pull_request_id=42)

        mock_complete.assert_not_called()

    def test_handles_complete_active_session_failure_gracefully(self, tmp_path, capsys):
        """Should print a warning to stderr but not crash when _complete_active_session raises."""
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
                "agentic_devtools.cli.azure_devops.file_review_commands._complete_active_session",
                side_effect=RuntimeError("lock timeout"),
            ):
                with patch("agentic_devtools.cli.azure_devops.file_review_commands.is_dry_run", return_value=False):
                    with patch(_AUTO_ADVANCE_PATCH, return_value=False):
                        # Should not raise
                        print_next_file_prompt(pull_request_id=42)

        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "complete review session" in captured.err
        # The completion message should still be printed (fallback since auto-advance returned False)
        assert "READY FOR DECISION" in captured.out

    def test_skips_complete_active_session_in_dry_run(self, tmp_path):
        """Should not call _complete_active_session when dry_run is enabled."""
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
                "agentic_devtools.cli.azure_devops.file_review_commands._complete_active_session",
            ) as mock_complete:
                with patch("agentic_devtools.cli.azure_devops.file_review_commands.is_dry_run", return_value=True):
                    with patch(_AUTO_ADVANCE_PATCH, return_value=True):
                        print_next_file_prompt(pull_request_id=42)

        mock_complete.assert_not_called()

    def test_auto_advance_called_when_all_complete(self, tmp_path):
        """Should call _try_advance_pr_review_to_decision when all files are reviewed."""
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
                "agentic_devtools.cli.azure_devops.file_review_commands._complete_active_session",
            ):
                with patch(_AUTO_ADVANCE_PATCH, return_value=True) as mock_advance:
                    print_next_file_prompt(pull_request_id=42)

        mock_advance.assert_called_once()

    def test_fallback_to_manual_when_auto_advance_returns_false(self, tmp_path, capsys):
        """Should print manual instruction when _try_advance_pr_review_to_decision returns False."""
        queue_data = {
            "pending": [],
            "completed": [{"path": "src/a.ts"}, {"path": "src/b.ts"}],
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.file_review_commands._complete_active_session",
            ):
                with patch(_AUTO_ADVANCE_PATCH, return_value=False):
                    print_next_file_prompt(pull_request_id=42)

        captured = capsys.readouterr()
        assert "READY FOR DECISION" in captured.out
        assert "YOUR NEXT ACTION: Run agdt-advance-workflow decision" in captured.out

    def test_fallback_to_manual_when_auto_advance_raises(self, tmp_path, capsys):
        """Should fall back to manual instruction when auto-advance raises an exception."""
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
                "agentic_devtools.cli.azure_devops.file_review_commands._complete_active_session",
            ):
                with patch(_AUTO_ADVANCE_PATCH, side_effect=RuntimeError("unexpected error")):
                    # Should not raise
                    print_next_file_prompt(pull_request_id=42)

        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "Auto-advance to decision failed" in captured.err
        assert "READY FOR DECISION" in captured.out
        assert "YOUR NEXT ACTION: Run agdt-advance-workflow decision" in captured.out

    def test_auto_advance_not_called_when_files_pending(self, tmp_path):
        """Should not call _try_advance_pr_review_to_decision when files remain pending."""
        queue_data = {
            "pending": [{"path": "src/app.py", "status": "pending"}],
            "completed": [{"path": "src/a.ts"}],
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.trigger_in_progress_for_file",
            ):
                with patch("agentic_devtools.cli.azure_devops.file_review_commands.is_dry_run", return_value=False):
                    with patch(_AUTO_ADVANCE_PATCH) as mock_advance:
                        print_next_file_prompt(pull_request_id=42)

        mock_advance.assert_not_called()

    def test_no_manual_instruction_when_auto_advance_succeeds(self, tmp_path, capsys):
        """Should NOT print manual instruction text when auto-advance returns True."""
        queue_data = {
            "pending": [],
            "completed": [{"path": "src/a.ts"}, {"path": "src/b.ts"}],
        }
        queue_file = tmp_path / "queue.json"
        queue_file.write_text(json.dumps(queue_data))

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands._get_queue_path",
            return_value=queue_file,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.file_review_commands._complete_active_session",
            ):
                with patch(_AUTO_ADVANCE_PATCH, return_value=True):
                    print_next_file_prompt(pull_request_id=42)

        captured = capsys.readouterr()
        assert "YOUR NEXT ACTION" not in captured.out
        assert "agdt-advance-workflow" not in captured.out
