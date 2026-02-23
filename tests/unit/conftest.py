"""
Shared fixtures for all unit tests.
"""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state.clear_state()
    yield


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
