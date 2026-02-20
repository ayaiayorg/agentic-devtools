"""Tests for agentic_devtools.background_tasks.run_function_in_background."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.background_tasks import run_function_in_background
from agentic_devtools.task_state import (
    BackgroundTask,
    TaskStatus,
    get_task_by_id,
)


@pytest.fixture
def mock_state_dir(tmp_path):
    """Fixture to mock the state directory."""
    with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path), patch(
        "agentic_devtools.task_state.get_state_dir", return_value=tmp_path
    ):
        yield tmp_path


class TestRunFunctionInBackground:
    """Tests for run_function_in_background function."""

    def test_returns_background_task(self, mock_state_dir):
        """Test run_function_in_background returns a BackgroundTask."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(pid=1)

            task = run_function_in_background("agentic_devtools.background_tasks", "cleanup_old_logs")

        assert isinstance(task, BackgroundTask)

    def test_uses_function_name_as_display_name(self, mock_state_dir):
        """Test display name defaults to function_name when not provided."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(pid=1)

            task = run_function_in_background("agentic_devtools.background_tasks", "cleanup_old_logs")

        assert task.command == "cleanup_old_logs"

    def test_uses_custom_display_name(self, mock_state_dir):
        """Test display name is used when command_display_name is provided."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(pid=1)

            task = run_function_in_background(
                "agentic_devtools.background_tasks",
                "cleanup_old_logs",
                command_display_name="agdt-tasks-clean",
            )

        assert task.command == "agdt-tasks-clean"

    def test_task_saved_with_pending_status(self, mock_state_dir):
        """Test task is saved with pending status after spawn."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(pid=1)

            task = run_function_in_background("agentic_devtools.background_tasks", "cleanup_old_logs")

            stored_task = get_task_by_id(task.id)
            assert stored_task.status == TaskStatus.PENDING

    def test_popen_called(self, mock_state_dir):
        """Test subprocess.Popen is called to spawn background process."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(pid=1)

            run_function_in_background("agentic_devtools.background_tasks", "cleanup_old_logs")

        mock_popen.assert_called_once()

    def test_task_has_unique_id(self, mock_state_dir):
        """Test each background task gets a unique ID."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(pid=1)

            task1 = run_function_in_background("agentic_devtools.background_tasks", "cleanup_old_logs")
            task2 = run_function_in_background("agentic_devtools.background_tasks", "cleanup_old_logs")

        assert task1.id != task2.id
