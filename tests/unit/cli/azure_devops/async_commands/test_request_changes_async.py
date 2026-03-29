"""Tests for request_changes_async function."""

import json
from unittest.mock import patch

from agentic_devtools.cli.azure_devops.async_commands import request_changes_async

_SUGGESTIONS = json.dumps([{"line": 42, "severity": "high", "content": "Missing null check"}])


class TestRequestChangesAsync:
    def test_enqueues_submission(self, mock_enqueue_and_state, capsys):
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "src/app/component.ts")
        set_value("file_review.summary", "Error handling issues found.")
        set_value("file_review.suggestions", _SUGGESTIONS)
        request_changes_async()
        captured = capsys.readouterr()
        assert "✅ Submission queued for src/app/component.ts" in captured.out
        mock_enqueue_and_state["mock_manager"].enqueue.assert_called_once_with(
            12345,
            "src/app/component.ts",
            "request-changes",
            "Error handling issues found.",
            suggestions=[{"line": 42, "severity": "high", "content": "Missing null check"}],
        )

    def test_calls_update_queue_after_review(self, mock_enqueue_and_state):
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "src/app/component.ts")
        set_value("file_review.summary", "Issues found.")
        set_value("file_review.suggestions", _SUGGESTIONS)
        request_changes_async()
        mock_enqueue_and_state["mock_update_queue"].assert_called_once_with(12345, "src/app/component.ts", "Changes")

    def test_calls_print_next_file_prompt(self, mock_enqueue_and_state):
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "src/app/component.ts")
        set_value("file_review.summary", "Issues found.")
        set_value("file_review.suggestions", _SUGGESTIONS)
        request_changes_async()
        mock_enqueue_and_state["mock_print_next"].assert_called_once_with(12345)

    def test_does_not_call_run_function_in_background(self, mock_enqueue_and_state):
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "src/app/component.ts")
        set_value("file_review.summary", "Issues found.")
        set_value("file_review.suggestions", _SUGGESTIONS)
        with patch("agentic_devtools.background_tasks.subprocess.Popen") as mock_popen:
            request_changes_async()
            mock_popen.assert_not_called()

    def test_accepts_cli_parameters(self, mock_enqueue_and_state, capsys):
        request_changes_async(
            file_path="src/cli/test.ts",
            summary="Issues found.",
            suggestions=_SUGGESTIONS,
            pull_request_id=99999,
        )
        captured = capsys.readouterr()
        assert "✅ Submission queued" in captured.out
        from agentic_devtools.state import get_value

        assert get_value("file_review.file_path") == "src/cli/test.ts"
        assert get_value("file_review.summary") == "Issues found."
        assert get_value("file_review.suggestions") == _SUGGESTIONS
