"""Tests for get_logs_dir function."""

from unittest.mock import patch

from agentic_devtools.task_state import get_logs_dir


class TestGetLogsDir:
    """Tests for get_logs_dir function."""

    def test_returns_logs_path_under_background_tasks_dir(self, tmp_path):
        """Should return logs subdirectory under background-tasks dir."""
        bg_dir = tmp_path / "background-tasks"
        bg_dir.mkdir(parents=True)

        with patch("agentic_devtools.task_state.get_background_tasks_dir", return_value=bg_dir):
            result = get_logs_dir()

        assert result == bg_dir / "logs"

    def test_creates_logs_directory(self, tmp_path):
        """Should create the logs directory if it does not exist."""
        bg_dir = tmp_path / "background-tasks"
        bg_dir.mkdir(parents=True)

        with patch("agentic_devtools.task_state.get_background_tasks_dir", return_value=bg_dir):
            result = get_logs_dir()

        assert result.exists()
        assert result.is_dir()

    def test_does_not_fail_if_logs_dir_already_exists(self, tmp_path):
        """Should not raise if logs directory already exists."""
        bg_dir = tmp_path / "background-tasks"
        logs_dir = bg_dir / "logs"
        logs_dir.mkdir(parents=True)

        with patch("agentic_devtools.task_state.get_background_tasks_dir", return_value=bg_dir):
            result = get_logs_dir()

        assert result.exists()
