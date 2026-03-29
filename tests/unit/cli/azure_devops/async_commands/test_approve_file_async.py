"""Tests for approve_file_async function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.async_commands import approve_file_async


class TestApproveFileAsync:
    def test_enqueues_submission(self, mock_enqueue_and_state, capsys):
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "src/app/component.ts")
        set_value("file_review.summary", "LGTM")
        approve_file_async()
        captured = capsys.readouterr()
        assert "✅ Submission queued for src/app/component.ts" in captured.out
        mock_enqueue_and_state["mock_manager"].enqueue.assert_called_once_with(
            12345, "src/app/component.ts", "approve", "LGTM"
        )

    def test_calls_update_queue_after_review(self, mock_enqueue_and_state):
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "src/app/component.ts")
        set_value("file_review.summary", "LGTM")
        approve_file_async()
        mock_enqueue_and_state["mock_update_queue"].assert_called_once_with(12345, "src/app/component.ts", "Approve")

    def test_calls_print_next_file_prompt(self, mock_enqueue_and_state):
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "src/app/component.ts")
        set_value("file_review.summary", "LGTM")
        approve_file_async()
        mock_enqueue_and_state["mock_print_next"].assert_called_once_with(12345)

    def test_does_not_call_run_function_in_background(self, mock_enqueue_and_state):
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "src/app/component.ts")
        set_value("file_review.summary", "LGTM")
        with patch("agentic_devtools.background_tasks.subprocess.Popen") as mock_popen:
            approve_file_async()
            mock_popen.assert_not_called()

    def test_accepts_summary_parameter(self, mock_enqueue_and_state, capsys):
        approve_file_async(
            file_path="src/cli/test.ts",
            summary="Clean implementation.",
            pull_request_id=99999,
        )
        captured = capsys.readouterr()
        assert "✅ Submission queued" in captured.out
        from agentic_devtools.state import get_value

        assert get_value("file_review.file_path") == "src/cli/test.ts"
        assert get_value("file_review.summary") == "Clean implementation."
        assert get_value("pull_request_id") == 99999

    def test_accepts_content_parameter_with_deprecation_warning(self, mock_enqueue_and_state, capsys):
        approve_file_async(
            file_path="src/cli/test.ts",
            content="Approved via CLI",
            pull_request_id=99999,
        )
        captured = capsys.readouterr()
        assert "✅ Submission queued" in captured.out
        assert "deprecated" in captured.err
        from agentic_devtools.state import get_value

        assert get_value("file_review.summary") == "Approved via CLI"

    def test_summary_takes_precedence_over_content(self, mock_enqueue_and_state, capsys):
        approve_file_async(
            file_path="src/cli/test.ts",
            summary="Summary wins",
            content="Should be ignored",
            pull_request_id=99999,
        )
        captured = capsys.readouterr()
        assert "✅ Submission queued" in captured.out
        assert "deprecated" not in captured.err
        from agentic_devtools.state import get_value

        assert get_value("file_review.summary") == "Summary wins"

    def test_content_state_key_fallback_without_cli_args(self, mock_enqueue_and_state, capsys):
        """When no CLI args are given and only 'content' exists in state,
        approve_file_async should fall back to it with a deprecation warning."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "src/app/legacy.ts")
        set_value("content", "Legacy LGTM")
        approve_file_async()
        captured = capsys.readouterr()
        assert "✅ Submission queued" in captured.out
        assert "deprecated" in captured.err
        from agentic_devtools.state import get_value

        assert get_value("file_review.summary") == "Legacy LGTM"
