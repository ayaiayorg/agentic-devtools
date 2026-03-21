"""Tests for agentic_devtools.background_tasks.run_in_background."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.background_tasks import run_in_background
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


class TestRunInBackground:
    """Tests for run_in_background function."""

    def test_returns_background_task(self, mock_state_dir):
        """Test run_in_background returns a BackgroundTask."""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            task = run_in_background("echo hello")

        assert isinstance(task, BackgroundTask)
        assert task.command == "echo hello"

    def test_task_has_unique_id(self, mock_state_dir):
        """Test each background task gets a unique ID."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(pid=1)

            task1 = run_in_background("cmd1")
            task2 = run_in_background("cmd2")

        assert task1.id != task2.id

    def test_creates_log_directory(self, mock_state_dir):
        """Test log directory is created as a side effect of run_in_background."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(pid=1)
            run_in_background("echo")

        # Logs directory should now exist under the mocked state dir
        logs_dir = mock_state_dir / "background-tasks" / "logs"
        assert logs_dir.exists()
        assert logs_dir.name == "logs"

    def test_popen_called(self, mock_state_dir):
        """Test subprocess.Popen is called to spawn background process."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(pid=1)

            run_in_background("agdt-test-cmd")

        # Verify Popen was called (with Python wrapper script)
        mock_popen.assert_called_once()

    def test_task_saved_with_pending_status(self, mock_state_dir):
        """Test task is saved with pending status after spawn (running status set by subprocess)."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(pid=1)

            task = run_in_background("echo")

            # Task should be pending (subprocess will set it to running)
            stored_task = get_task_by_id(task.id)
            assert stored_task.status == TaskStatus.PENDING


class TestRunInBackgroundIntegration:
    """Integration tests for run_in_background."""

    def test_multiple_background_tasks(self, mock_state_dir):
        """Test running multiple background tasks."""
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock(pid=1)

            task1 = run_in_background("cmd1")
            task2 = run_in_background("cmd2")
            task3 = run_in_background("cmd3")

        # All should have unique IDs
        ids = {task1.id, task2.id, task3.id}
        assert len(ids) == 3

        # All should be retrievable
        assert get_task_by_id(task1.id) is not None
        assert get_task_by_id(task2.id) is not None
        assert get_task_by_id(task3.id) is not None
