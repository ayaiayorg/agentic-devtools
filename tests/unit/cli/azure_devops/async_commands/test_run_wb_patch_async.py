"""Tests for run_wb_patch_async function."""

from agentic_devtools.cli.azure_devops.async_commands import run_wb_patch_async
from tests.unit.cli.azure_devops.async_commands._helpers import assert_function_in_script, get_script_from_call


class TestRunWbPatchAsync:
    def test_spawns_background_task(self, mock_background_and_state, capsys):
        run_wb_patch_async()
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(script, "agentic_devtools.cli.azure_devops.pipeline_commands", "run_wb_patch")
