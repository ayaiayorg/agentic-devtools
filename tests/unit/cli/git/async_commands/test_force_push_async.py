"""Tests for agentic_devtools.cli.git.async_commands.force_push_async."""

from agentic_devtools.cli.git.async_commands import force_push_async
from tests.unit.cli.git.async_commands.conftest import assert_function_in_script, get_script_from_call


class TestForcePushAsync:
    """Tests for force_push_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test force_push_async spawns a background task calling the correct function."""
        force_push_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(script, "agentic_devtools.cli.git.commands", "force_push_cmd")

    def test_importable(self):
        """Test force_push_async can be imported and is callable."""
        assert callable(force_push_async)
