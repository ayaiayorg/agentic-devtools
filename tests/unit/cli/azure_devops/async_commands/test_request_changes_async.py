"""Tests for request_changes_async function."""
import pytest
from agentic_devtools.cli.azure_devops.async_commands import request_changes_async
from tests.unit.cli.azure_devops.async_commands._helpers import get_script_from_call, assert_function_in_script


class TestRequestChangesAsync:
    def test_spawns_background_task(self, mock_background_and_state, capsys):
        from agentic_devtools.state import set_value
        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "src/app/component.ts")
        set_value("content", "Please fix this issue")
        set_value("line", 42)
        request_changes_async()
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(script, "agentic_devtools.cli.azure_devops.file_review_commands", "request_changes")

    def test_accepts_cli_parameters(self, mock_background_and_state, capsys):
        request_changes_async(
            file_path="src/cli/test.ts",
            content="Issue via CLI",
            line=100,
            pull_request_id=99999,
        )
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        from agentic_devtools.state import get_value
        assert get_value("file_review.file_path") == "src/cli/test.ts"
        assert get_value("content") == "Issue via CLI"
        assert get_value("line") == 100
