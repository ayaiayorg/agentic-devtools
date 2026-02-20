"""Tests for approve_pull_request_async function."""

from agentic_devtools.cli.azure_devops.async_commands import approve_pull_request_async
from tests.unit.cli.azure_devops.async_commands._helpers import assert_function_in_script, get_script_from_call


class TestApprovePullRequestAsync:
    def test_spawns_background_task(self, mock_background_and_state, capsys):
        from agentic_devtools.state import set_value

        set_value("pull_request_id", "12345")
        approve_pull_request_async()
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(script, "agentic_devtools.cli.azure_devops.commands", "approve_pull_request")
