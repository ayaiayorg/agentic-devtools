"""Tests for mark_file_reviewed_async function."""
import pytest
from agentic_devtools.cli.azure_devops.async_commands import mark_file_reviewed_async
from tests.unit.cli.azure_devops.async_commands._helpers import get_script_from_call, assert_function_in_script


class TestMarkFileReviewedAsync:
    def test_spawns_background_task(self, mock_background_and_state, capsys):
        mark_file_reviewed_async()
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(script, "agentic_devtools.cli.azure_devops.mark_reviewed", "mark_file_reviewed_cli")
