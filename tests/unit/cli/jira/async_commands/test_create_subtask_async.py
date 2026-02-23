"""
Tests for Jira async commands and write_async_status function.
"""

from unittest.mock import patch

import pytest

from agdt_ai_helpers.cli.jira.async_commands import (
    create_subtask_async,
)


def _get_script_from_call(mock_popen):
    """Extract the Python script from the Popen call args."""
    call_args = mock_popen.call_args[0][0]  # First positional arg is the command list
    # Script is the third element: [python, -c, <script>]
    return call_args[2] if len(call_args) > 2 else ""


def _assert_function_in_script(script, module_path, function_name):
    """Assert the script calls the expected function from the expected module."""
    assert f"module_path = '{module_path}'" in script, f"Expected module_path = '{module_path}' in script"
    assert f"function_name = '{function_name}'" in script, f"Expected function_name = '{function_name}' in script"


class TestCreateSubtaskAsync:
    """Tests for create_subtask_async command."""

    def test_requires_parent_key(self, mock_background_and_state):
        """Test create_subtask_async requires parent_key."""
        with patch("agdt_ai_helpers.cli.jira.async_commands.get_jira_value", return_value=None):
            with pytest.raises(SystemExit):
                create_subtask_async()

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test create_subtask_async spawns a background task."""
        with patch(
            "agdt_ai_helpers.cli.jira.async_commands.get_jira_value",
            side_effect=lambda k: {"parent_key": "DFLY-123", "summary": "Subtask"}.get(k),
        ):
            create_subtask_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        assert "DFLY-123" in captured.out
