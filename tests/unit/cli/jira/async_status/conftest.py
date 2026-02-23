"""
Shared fixtures for tests/unit/cli/jira/async_status/.

These fixtures patch agdt_ai_helpers (the legacy shim) module paths, as the Jira
async tests use that import path directly rather than agentic_devtools.
The temp_state_dir here patches async_status.get_state_dir (the module actually
used by the async command layer) instead of the top-level state module.
"""

from unittest.mock import MagicMock, patch

import pytest

from agdt_ai_helpers.cli.jira import async_status


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files, patching async_status.get_state_dir."""
    with patch.object(async_status, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def mock_background_and_state(tmp_path):
    """Mock both background task infrastructure and Jira state."""
    with patch("agdt_ai_helpers.state.get_state_dir", return_value=tmp_path):
        with patch("agdt_ai_helpers.task_state.get_state_dir", return_value=tmp_path):
            with patch("agdt_ai_helpers.background_tasks.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.pid = 12345
                mock_popen.return_value = mock_process
                yield {
                    "state_dir": tmp_path,
                    "mock_popen": mock_popen,
                }
