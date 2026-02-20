"""Tests for agentic_devtools.cli.git.async_commands.push_async."""

from agentic_devtools.cli.git.async_commands import push_async
from tests.unit.cli.git.async_commands.conftest import assert_function_in_script, get_script_from_call


class TestPushAsync:
    """Tests for push_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test push_async spawns a background task calling the correct function."""
        push_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(script, "agentic_devtools.cli.git.commands", "push_cmd")

    def test_importable(self):
        """Test push_async can be imported and is callable."""
        assert callable(push_async)
