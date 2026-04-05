"""Tests for agentic_devtools.cli.git.async_commands.commit_async."""

import re

import pytest

from agentic_devtools.cli.git.async_commands import commit_async
from tests.unit.cli.git.async_commands._helpers import assert_function_in_script, get_script_from_call


class TestCommitAsync:
    """Tests for commit_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test commit_async spawns a background task calling the correct function."""
        commit_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(script, "agentic_devtools.cli.git.commands", "commit_cmd")

    def test_prints_tracking_instructions(self, mock_background_and_state, capsys):
        """Test tracking instructions are printed."""
        commit_async()

        captured = capsys.readouterr()
        assert "agdt-task-wait" in captured.out

    def test_message_parameter_saves_to_state(self, mock_background_and_state, capsys):
        """Test --message parameter saves to state."""
        from agentic_devtools.state import get_value

        commit_async(_argv=["--message", "test commit message"])

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        assert get_value("commit_message") == "test commit message"

    def test_short_m_parameter_saves_to_state(self, mock_background_and_state, capsys):
        """Test -m short parameter saves to state."""
        from agentic_devtools.state import get_value

        commit_async(_argv=["-m", "short message"])

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        assert get_value("commit_message") == "short message"

    def test_commit_message_alias_saves_to_state(self, mock_background_and_state, capsys):
        """Test --commit-message alias saves to state."""
        from agentic_devtools.state import get_value

        commit_async(_argv=["--commit-message", "aliased message"])

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        assert get_value("commit_message") == "aliased message"

    def test_function_message_parameter(self, mock_background_and_state, capsys):
        """Test message function parameter saves to state."""
        from agentic_devtools.state import get_value

        commit_async(message="function param message")

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        assert get_value("commit_message") == "function param message"

    def test_cli_args_override_function_params(self, mock_background_and_state, capsys):
        """Test CLI args take precedence over function parameters."""
        from agentic_devtools.state import get_value

        commit_async(message="function msg", _argv=["-m", "cli msg"])

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        assert get_value("commit_message") == "cli msg"

    def test_help_flag_shows_help(self, mock_background_and_state, capsys):
        """Test --help shows usage information."""
        with pytest.raises(SystemExit) as exc_info:
            commit_async(_argv=["--help"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Save work" in captured.out
        assert "--message" in captured.out or "-m" in captured.out

    def test_task_ids_are_unique(self, mock_background_and_state, capsys):
        """Test each spawned task gets a unique ID."""
        commit_async()
        out1 = capsys.readouterr().out

        commit_async()
        out2 = capsys.readouterr().out

        id1_match = re.search(r"Background task started \(command: [^,]+, id: ([a-f0-9-]+)\)", out1)
        id2_match = re.search(r"Background task started \(command: [^,]+, id: ([a-f0-9-]+)\)", out2)
        assert id1_match is not None, f"No task ID found in: {out1}"
        assert id2_match is not None, f"No task ID found in: {out2}"
        assert id1_match.group(1) != id2_match.group(1)

    def test_importable(self):
        """Test commit_async can be imported and is callable."""
        assert callable(commit_async)

    def test_skip_stage_flag_saves_to_state(self, mock_background_and_state, capsys):
        """Test --skip-stage flag saves skip_stage to state as 'true'."""
        from agentic_devtools.state import get_value

        commit_async(_argv=["--skip-stage"])

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        assert get_value("skip_stage") == "true"

    def test_skip_push_flag_saves_to_state(self, mock_background_and_state, capsys):
        """Test --skip-push flag saves skip_push to state as 'true'."""
        from agentic_devtools.state import get_value

        commit_async(_argv=["--skip-push"])

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        assert get_value("skip_push") == "true"

    def test_combined_flags_save_to_state(self, mock_background_and_state, capsys):
        """Test --dry-run --skip-stage --skip-push all save correctly."""
        from agentic_devtools.state import get_value

        commit_async(_argv=["--dry-run", "--skip-stage", "--skip-push"])

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        assert get_value("dry_run") == "true"
        assert get_value("skip_stage") == "true"
        assert get_value("skip_push") == "true"

    def test_skip_stage_function_param_saves_to_state(self, mock_background_and_state, capsys):
        """Test skip_stage=True function parameter saves to state."""
        from agentic_devtools.state import get_value

        commit_async(skip_stage=True)

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        assert get_value("skip_stage") == "true"

    def test_skip_push_function_param_saves_to_state(self, mock_background_and_state, capsys):
        """Test skip_push=True function parameter saves to state."""
        from agentic_devtools.state import get_value

        commit_async(skip_push=True)

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        assert get_value("skip_push") == "true"

    def test_skip_stage_set_to_false_when_not_specified(self, mock_background_and_state, capsys):
        """Test skip_stage is set to 'false' in state when not specified."""
        from agentic_devtools.state import get_value

        commit_async(_argv=[])

        assert get_value("skip_stage") == "false"

    def test_skip_push_set_to_false_when_not_specified(self, mock_background_and_state, capsys):
        """Test skip_push is set to 'false' in state when not specified."""
        from agentic_devtools.state import get_value

        commit_async(_argv=[])

        assert get_value("skip_push") == "false"
