"""Tests for agentic_devtools.background_tasks.get_task_log_content."""

import pytest
from unittest.mock import patch

from agentic_devtools.background_tasks import get_task_log_content
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


class TestGetTaskLogContent:
    """Tests for get_task_log_content function."""

    def test_returns_log_content(self, mock_state_dir):
        """Test get_task_log_content returns file content."""
        # Create log file path within mock state dir
        log_path = mock_state_dir / "logs" / "test-task.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("Log line 1\nLog line 2\n")

        # Create a task with the log file
        task = BackgroundTask.create(command="cmd", log_file=log_path)
        add_task(task)

        content = get_task_log_content(task.id)

        assert content is not None
        assert "Log line 1" in content
        assert "Log line 2" in content

    def test_returns_none_for_missing_file(self, mock_state_dir):
        """Test returns None if log file doesn't exist."""
        task = BackgroundTask.create(command="cmd")
        add_task(task)

        # Don't create the log file
        content = get_task_log_content(task.id)

        assert content is None

    def test_returns_none_for_nonexistent_task(self, mock_state_dir):
        """Test returns None for non-existent task ID."""
        content = get_task_log_content("nonexistent-task-id")
        assert content is None

    def test_handles_unicode_content(self, mock_state_dir):
        """Test handles unicode characters in log."""
        # Create log file path within mock state dir
        log_path = mock_state_dir / "logs" / "unicode-task.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("Unicode: äöü 日本語 🎉", encoding="utf-8")

        # Create a task with the log file
        task = BackgroundTask.create(command="cmd", log_file=log_path)
        add_task(task)

        content = get_task_log_content(task.id)

        assert content is not None
        assert "Unicode" in content
        assert "äöü" in content
