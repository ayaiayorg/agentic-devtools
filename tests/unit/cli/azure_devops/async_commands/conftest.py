"""
Shared fixtures for async_commands tests.
"""

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
