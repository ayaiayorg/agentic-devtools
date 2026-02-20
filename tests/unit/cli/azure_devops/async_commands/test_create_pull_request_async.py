"""Tests for create_pull_request_async function."""

from agentic_devtools.cli.azure_devops.async_commands import create_pull_request_async
from tests.unit.cli.azure_devops.async_commands._helpers import assert_function_in_script, get_script_from_call


class TestCreatePullRequestAsync:
    def test_spawns_background_task(self, mock_background_and_state, capsys):
        from agentic_devtools.state import set_value

        set_value("source_branch", "feature/test-branch")
        set_value("title", "Test PR title")
        create_pull_request_async()
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(script, "agentic_devtools.cli.azure_devops.commands", "create_pull_request")

    def test_accepts_cli_parameters(self, mock_background_and_state, capsys):
        create_pull_request_async(
            source_branch="feature/cli-branch",
            title="CLI PR title",
            description="CLI description",
        )
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        from agentic_devtools.state import get_value

        assert get_value("source_branch") == "feature/cli-branch"
        assert get_value("title") == "CLI PR title"
        assert get_value("description") == "CLI description"
