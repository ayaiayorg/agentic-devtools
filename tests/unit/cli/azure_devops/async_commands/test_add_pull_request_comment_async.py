"""Tests for add_pull_request_comment_async function."""
import pytest
from agentic_devtools.cli.azure_devops.async_commands import add_pull_request_comment_async
from tests.unit.cli.azure_devops.async_commands._helpers import get_script_from_call, assert_function_in_script


class TestAddPullRequestCommentAsync:
    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test command spawns a background task calling the correct function."""
        from agentic_devtools.state import set_value
        set_value("pull_request_id", "12345")
        set_value("content", "Test comment")
        add_pull_request_comment_async()
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(script, "agentic_devtools.cli.azure_devops.commands", "add_pull_request_comment")
