"""Shared fixtures for tests/unit/cli/git/async_commands/."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_background_and_state(tmp_path):
    """Mock both background task infrastructure and state."""
    with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
        with patch("agentic_devtools.task_state.get_state_dir", return_value=tmp_path):
            with patch("agentic_devtools.background_tasks.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.pid = 12345
                mock_popen.return_value = mock_process
                yield {
                    "state_dir": tmp_path,
                    "mock_popen": mock_popen,
                }


def get_script_from_call(mock_popen):
    """Extract the Python script from the Popen call args."""
    call_args = mock_popen.call_args[0][0]
    return call_args[2] if len(call_args) > 2 else ""


def assert_function_in_script(script: str, module_path: str, function_name: str):
    """Assert that the generated script calls the correct module and function."""
    assert f"module_path = '{module_path}'" in script, f"Expected module_path='{module_path}' in script"
    assert f"function_name = '{function_name}'" in script, f"Expected function_name='{function_name}' in script"
