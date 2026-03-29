"""
Shared fixtures for all unit tests.
"""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from tests.helpers import make_mock_popen


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
            with patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_state_dir",
                return_value=tmp_path,
            ):
                with patch("agentic_devtools.background_tasks.subprocess.Popen") as mock_popen:
                    mock_popen.return_value = make_mock_popen()
                    yield {
                        "state_dir": tmp_path,
                        "mock_popen": mock_popen,
                    }


@pytest.fixture
def mock_enqueue_and_state(tmp_path):
    """Mock SubmissionManager singleton, queue update, and state for file review commands."""
    mock_manager = MagicMock()
    mock_manager.enqueue.return_value = MagicMock()
    with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
        with patch("agentic_devtools.task_state.get_state_dir", return_value=tmp_path):
            with patch(
                "agentic_devtools.cli.azure_devops.file_review_commands.get_state_dir",
                return_value=tmp_path,
            ):
                with patch(
                    "agentic_devtools.submission_manager_instance.get_submission_manager",
                    return_value=mock_manager,
                ) as mock_get_sm:
                    with patch(
                        "agentic_devtools.cli.azure_devops.file_review_commands._update_queue_after_review",
                    ) as mock_update_queue:
                        with patch(
                            "agentic_devtools.cli.azure_devops.file_review_commands.print_next_file_prompt",
                        ) as mock_print_next:
                            yield {
                                "state_dir": tmp_path,
                                "mock_manager": mock_manager,
                                "mock_get_sm": mock_get_sm,
                                "mock_update_queue": mock_update_queue,
                                "mock_print_next": mock_print_next,
                            }
