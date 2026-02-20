"""Tests for approve_file_async function."""
import pytest
from agentic_devtools.cli.azure_devops.async_commands import approve_file_async
from tests.unit.cli.azure_devops.async_commands._helpers import get_script_from_call, assert_function_in_script


class TestApproveFileAsync:
    def test_spawns_background_task(self, mock_background_and_state, capsys):
        from agentic_devtools.state import set_value
        set_value("pull_request_id", 12345)
        set_value("file_review.file_path", "src/app/component.ts")
        set_value("content", "LGTM")
        approve_file_async()
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(script, "agentic_devtools.cli.azure_devops.file_review_commands", "approve_file")

    def test_accepts_cli_parameters(self, mock_background_and_state, capsys):
        approve_file_async(
            file_path="src/cli/test.ts",
            content="Approved via CLI",
            pull_request_id=99999,
        )
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        from agentic_devtools.state import get_value
        assert get_value("file_review.file_path") == "src/cli/test.ts"
        assert get_value("content") == "Approved via CLI"
        assert get_value("pull_request_id") == 99999
