"""Tests for resolve_thread_async function."""
import pytest
from agentic_devtools.cli.azure_devops.async_commands import resolve_thread_async
from tests.unit.cli.azure_devops.async_commands._helpers import get_script_from_call, assert_function_in_script


class TestResolveThreadAsync:
    def test_spawns_background_task(self, mock_background_and_state, capsys):
        from agentic_devtools.state import set_value
        set_value("pull_request_id", "12345")
        set_value("thread_id", "67890")
        resolve_thread_async()
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(script, "agentic_devtools.cli.azure_devops.commands", "resolve_thread")
