"""
Tests for Jira async commands and write_async_status function.
"""

from unittest.mock import MagicMock, patch

import pytest

from agdt_ai_helpers.cli.jira import async_status
from agdt_ai_helpers.cli.jira.async_commands import (
    find_role_id_by_name_async,
)


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    # Patch where get_state_dir is used (in async_status module)
    with patch.object(async_status, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def mock_background_and_state(tmp_path):
    """Mock both background task infrastructure and Jira state."""
    # Need to patch get_state_dir in both modules since task_state imports it directly
    with patch("agdt_ai_helpers.state.get_state_dir", return_value=tmp_path):
        with patch("agdt_ai_helpers.task_state.get_state_dir", return_value=tmp_path):
            # Patch subprocess.Popen only in the background_tasks module, not globally
            # This prevents interference with subprocess.run usage in state.py
            with patch("agdt_ai_helpers.background_tasks.subprocess.Popen") as mock_popen:
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


def _assert_function_in_script(script, module_path, function_name):
    """Assert the script calls the expected function from the expected module."""
    assert f"module_path = '{module_path}'" in script, f"Expected module_path = '{module_path}' in script"
    assert f"function_name = '{function_name}'" in script, f"Expected function_name = '{function_name}' in script"


class TestRoleCommandsAsync:
    """Tests for role management async commands."""

    def test_find_role_id_spawns_task(self, mock_background_and_state, capsys):
        """Test find_role_id_by_name_async spawns background task."""
        with patch(
            "agdt_ai_helpers.cli.jira.async_commands.get_jira_value",
            side_effect=lambda k: {"project_key": "DFLY", "role_name": "Developers"}.get(k),
        ):
            find_role_id_by_name_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

