"""Tests for get_pull_request_details_async function."""

from agentic_devtools.cli.azure_devops.async_commands import get_pull_request_details_async
from tests.unit.cli.azure_devops.async_commands._helpers import assert_function_in_script, get_script_from_call


class TestGetPullRequestDetailsAsync:
    def test_spawns_background_task(self, mock_background_and_state, capsys):
        get_pull_request_details_async()
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(
            script, "agentic_devtools.cli.azure_devops.pull_request_details_commands", "get_pull_request_details"
        )
