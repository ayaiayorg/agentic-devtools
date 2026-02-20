"""Tests for agentic_devtools.cli.git.async_commands.stage_async."""

from agentic_devtools.cli.git.async_commands import stage_async
from tests.unit.cli.git.async_commands._helpers import assert_function_in_script, get_script_from_call


class TestStageAsync:
    """Tests for stage_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test stage_async spawns a background task calling the correct function."""
        stage_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(script, "agentic_devtools.cli.git.commands", "stage_cmd")

    def test_importable(self):
        """Test stage_async can be imported and is callable."""
        assert callable(stage_async)
