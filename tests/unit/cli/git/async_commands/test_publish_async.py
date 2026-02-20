"""Tests for agentic_devtools.cli.git.async_commands.publish_async."""

from agentic_devtools.cli.git.async_commands import publish_async
from tests.unit.cli.git.async_commands.conftest import assert_function_in_script, get_script_from_call


class TestPublishAsync:
    """Tests for publish_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test publish_async spawns a background task calling the correct function."""
        publish_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(script, "agentic_devtools.cli.git.commands", "publish_cmd")

    def test_importable(self):
        """Test publish_async can be imported and is callable."""
        assert callable(publish_async)
