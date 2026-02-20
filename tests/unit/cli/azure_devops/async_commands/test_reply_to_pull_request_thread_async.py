"""Tests for reply_to_pull_request_thread_async function."""
from agentic_devtools.cli.azure_devops.async_commands import reply_to_pull_request_thread_async
from tests.unit.cli.azure_devops.async_commands._helpers import assert_function_in_script, get_script_from_call


class TestReplyToThreadAsync:
    def test_spawns_background_task(self, mock_background_and_state, capsys):
        from agentic_devtools.state import set_value
        set_value("pull_request_id", "12345")
        set_value("thread_id", "67890")
        set_value("content", "Test reply")
        reply_to_pull_request_thread_async()
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(script, "agentic_devtools.cli.azure_devops.commands", "reply_to_pull_request_thread")
