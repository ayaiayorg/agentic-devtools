"""
Tests for Jira async commands and write_async_status function.
"""

from unittest.mock import patch

import pytest

from agdt_ai_helpers.cli.jira.async_commands import (
    add_comment_async,
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


class TestAddCommentAsync:
    """Tests for add_comment_async command."""

    def test_requires_issue_key(self, mock_background_and_state):
        """Test add_comment_async requires issue_key."""
        with patch("agdt_ai_helpers.cli.jira.async_commands.get_jira_value", return_value=None):
            with pytest.raises(SystemExit):
                add_comment_async()

    def test_requires_comment(self, mock_background_and_state):
        """Test add_comment_async requires comment."""
        with patch(
            "agdt_ai_helpers.cli.jira.async_commands.get_jira_value",
            side_effect=lambda k: "DFLY-123" if k == "issue_key" else None,
        ):
            with pytest.raises(SystemExit):
                add_comment_async()

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test add_comment_async spawns a background task calling the correct function."""
        with patch(
            "agdt_ai_helpers.cli.jira.async_commands.get_jira_value",
            side_effect=lambda k: {"issue_key": "DFLY-123", "comment": "Test comment"}.get(k),
        ):
            add_comment_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        # Verify the generated script calls the correct function
        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "agentic_devtools.cli.jira.comment_commands", "add_comment")
