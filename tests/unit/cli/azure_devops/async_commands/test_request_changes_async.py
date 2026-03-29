"""Tests for request_changes_async function."""

import json

from agentic_devtools.cli.azure_devops.async_commands import request_changes_async
from tests.unit.cli.azure_devops.async_commands._helpers import assert_function_in_script, get_script_from_call

_SUGGESTIONS = json.dumps([{"line": 42, "severity": "high", "content": "Missing null check"}])


class TestRequestChangesAsync:
    def test_spawns_background_task(self, mock_background_and_state, capsys):
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "src/app/component.ts")
        set_value("file_review.summary", "Error handling issues found.")
        set_value("file_review.suggestions", _SUGGESTIONS)
        request_changes_async()
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(script, "agentic_devtools.cli.azure_devops.file_review_commands", "request_changes")

    def test_accepts_cli_parameters(self, mock_background_and_state, capsys):
        request_changes_async(
            file_path="src/cli/test.ts",
            summary="Issues found.",
            suggestions=_SUGGESTIONS,
            pull_request_id=99999,
        )
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        from agentic_devtools.state import get_value

        assert get_value("file_review.file_path") == "src/cli/test.ts"
        assert get_value("file_review.summary") == "Issues found."
        assert get_value("file_review.suggestions") == _SUGGESTIONS
