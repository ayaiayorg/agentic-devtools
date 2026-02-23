"""Tests for agentic_devtools.cli.git.async_commands.amend_async."""

from agentic_devtools.cli.git.async_commands import amend_async
from tests.unit.cli.git.async_commands._helpers import assert_function_in_script, get_script_from_call


class TestAmendAsync:
    """Tests for amend_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test amend_async spawns a background task calling the correct function."""
        amend_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(script, "agentic_devtools.cli.git.commands", "amend_cmd")

    def test_prints_tracking_instructions(self, mock_background_and_state, capsys):
        """Test tracking instructions are printed."""
        amend_async()

        captured = capsys.readouterr()
        assert "agdt-task-wait" in captured.out

    def test_message_parameter_saves_to_state(self, mock_background_and_state, capsys):
        """Test --message parameter saves to state."""
        from agentic_devtools.state import get_value

        amend_async(_argv=["--message", "amend message"])

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        assert get_value("commit_message") == "amend message"

    def test_short_m_parameter_saves_to_state(self, mock_background_and_state, capsys):
        """Test -m short parameter saves to state."""
        from agentic_devtools.state import get_value

        amend_async(_argv=["-m", "short amend msg"])

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        assert get_value("commit_message") == "short amend msg"

    def test_function_message_parameter(self, mock_background_and_state, capsys):
        """Test message function parameter saves to state."""
        from agentic_devtools.state import get_value

        amend_async(message="func amend msg")

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        assert get_value("commit_message") == "func amend msg"

    def test_importable(self):
        """Test amend_async can be imported and is callable."""
        assert callable(amend_async)
