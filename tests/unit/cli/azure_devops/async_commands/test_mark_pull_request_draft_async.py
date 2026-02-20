"""Tests for mark_pull_request_draft_async function."""
import pytest
from agentic_devtools.cli.azure_devops.async_commands import mark_pull_request_draft_async
from tests.unit.cli.azure_devops.async_commands._helpers import get_script_from_call, assert_function_in_script


class TestMarkPullRequestDraftAsync:
    def test_spawns_background_task(self, mock_background_and_state, capsys):
        mark_pull_request_draft_async()
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(script, "agentic_devtools.cli.azure_devops.commands", "mark_pull_request_draft")
