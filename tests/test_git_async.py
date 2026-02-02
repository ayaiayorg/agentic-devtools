"""
Tests for Git async commands.

Tests verify that async commands spawn background tasks correctly,
calling Python functions directly via run_function_in_background.
"""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.git.async_commands import (
    amend_async,
    commit_async,
    force_push_async,
    publish_async,
    push_async,
    stage_async,
)


@pytest.fixture
def mock_background_and_state(tmp_path):
    """Mock both background task infrastructure and state."""
    # Need to patch get_state_dir in both modules since task_state imports it directly
    with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
        with patch("agentic_devtools.task_state.get_state_dir", return_value=tmp_path):
            # Patch subprocess.Popen only in the background_tasks module, not globally
            # This prevents interference with subprocess.run usage in state.py
            with patch("agentic_devtools.background_tasks.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.pid = 12345
                mock_popen.return_value = mock_process
                yield {
                    "state_dir": tmp_path,
                    "mock_popen": mock_popen,
                }


def _get_script_from_call(mock_popen):
    """Extract the Python script from the Popen call args."""
    call_args = mock_popen.call_args[0][0]  # First positional arg is the command list
    # Script is the third element: [python, -c, <script>]
    return call_args[2] if len(call_args) > 2 else ""


def _assert_function_in_script(script: str, module_path: str, function_name: str):
    """Assert that the generated script calls the correct module and function."""
    assert f"module_path = '{module_path}'" in script, f"Expected module_path='{module_path}' in script"
    assert f"function_name = '{function_name}'" in script, f"Expected function_name='{function_name}' in script"


class TestCommitAsync:
    """Tests for commit_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test commit_async spawns a background task calling the correct function."""
        commit_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.git.commands", "commit_cmd")

    def test_prints_tracking_instructions(self, mock_background_and_state, capsys):
        """Test tracking instructions are printed."""
        commit_async()

        captured = capsys.readouterr()
        # Simplified output now only shows dfly-task-wait
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


class TestAmendAsync:
    """Tests for amend_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test amend_async spawns a background task calling the correct function."""
        amend_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.git.commands", "amend_cmd")

    def test_prints_tracking_instructions(self, mock_background_and_state, capsys):
        """Test tracking instructions are printed."""
        amend_async()

        captured = capsys.readouterr()
        # Simplified output now only shows dfly-task-wait
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


class TestStageAsync:
    """Tests for stage_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test stage_async spawns a background task calling the correct function."""
        stage_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.git.commands", "stage_cmd")


class TestPushAsync:
    """Tests for push_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test push_async spawns a background task calling the correct function."""
        push_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.git.commands", "push_cmd")


class TestForcePushAsync:
    """Tests for force_push_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test force_push_async spawns a background task calling the correct function."""
        force_push_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.git.commands", "force_push_cmd")


class TestPublishAsync:
    """Tests for publish_async command."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test publish_async spawns a background task calling the correct function."""
        publish_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.git.commands", "publish_cmd")


class TestGitAsyncIntegration:
    """Integration tests for Git async commands."""

    def test_all_commands_importable(self):
        """Test all async commands can be imported."""
        from agentic_devtools.cli.git.async_commands import (
            amend_async,
            commit_async,
            force_push_async,
            publish_async,
            push_async,
            stage_async,
        )

        # All should be callable
        assert callable(commit_async)
        assert callable(amend_async)
        assert callable(stage_async)
        assert callable(push_async)
        assert callable(force_push_async)
        assert callable(publish_async)

    def test_task_ids_are_unique(self, mock_background_and_state, capsys):
        """Test each spawned task gets a unique ID."""
        commit_async()
        out1 = capsys.readouterr().out

        amend_async()
        out2 = capsys.readouterr().out

        # Extract task IDs from output (new format - match the first occurrence per output)
        import re

        # Use the "Background task started (command: ..., id: ...)" pattern
        id1_match = re.search(r"Background task started \(command: [^,]+, id: ([a-f0-9-]+)\)", out1)
        id2_match = re.search(r"Background task started \(command: [^,]+, id: ([a-f0-9-]+)\)", out2)
        assert id1_match is not None, f"No task ID found in: {out1}"
        assert id2_match is not None, f"No task ID found in: {out2}"
        assert id1_match.group(1) != id2_match.group(1)
