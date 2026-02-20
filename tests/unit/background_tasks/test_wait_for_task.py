"""Tests for agentic_devtools.background_tasks.wait_for_task."""

import time
from unittest.mock import patch

import pytest

from agentic_devtools.background_tasks import wait_for_task
from agentic_devtools.task_state import (
    BackgroundTask,
    add_task,
)


@pytest.fixture
def mock_state_dir(tmp_path):
    """Fixture to mock the state directory."""
    with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path), patch(
        "agentic_devtools.task_state.get_state_dir", return_value=tmp_path
    ):
        yield tmp_path


class TestWaitForTask:
    """Tests for wait_for_task function."""

    def test_returns_immediately_for_completed_task(self, mock_state_dir):
        """Test wait returns immediately for completed task."""
        task = BackgroundTask.create(command="cmd")
        task.mark_completed(exit_code=0)
        add_task(task)

        success, exit_code = wait_for_task(task.id, timeout=1.0)

        assert success is True
        assert exit_code == 0

    def test_returns_immediately_for_failed_task(self, mock_state_dir):
        """Test wait returns immediately for failed task."""
        task = BackgroundTask.create(command="cmd")
        task.mark_failed(exit_code=1)
        add_task(task)

        success, exit_code = wait_for_task(task.id, timeout=1.0)

        assert success is False
        assert exit_code == 1

    def test_returns_none_for_nonexistent_task(self, mock_state_dir):
        """Test wait returns (False, None) for non-existent task."""
        success, exit_code = wait_for_task("nonexistent-task-id", timeout=1.0)

        assert success is False
        assert exit_code is None

    def test_times_out_for_running_task(self, mock_state_dir):
        """Test wait times out for running task."""
        task = BackgroundTask.create(command="cmd")
        task.mark_running()
        add_task(task)

        start = time.time()
        success, exit_code = wait_for_task(task.id, timeout=0.5, poll_interval=0.1)
        elapsed = time.time() - start

        assert success is False
        assert exit_code is None
        assert elapsed >= 0.4  # Should have waited for timeout
