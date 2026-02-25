"""Tests for get_background_tasks_dir function."""

from unittest.mock import patch

from agentic_devtools.task_state import get_background_tasks_dir


class TestGetBackgroundTasksDir:
    """Tests for get_background_tasks_dir function."""

    def test_returns_path_under_state_dir(self, tmp_path):
        """Should return background-tasks subdirectory under state dir."""
        with patch("agentic_devtools.task_state.get_state_dir", return_value=tmp_path):
            result = get_background_tasks_dir()

        assert result == tmp_path / "background-tasks"

    def test_creates_directory(self, tmp_path):
        """Should create the directory if it does not exist."""
        with patch("agentic_devtools.task_state.get_state_dir", return_value=tmp_path):
            result = get_background_tasks_dir()

        assert result.exists()
        assert result.is_dir()

    def test_does_not_fail_if_directory_already_exists(self, tmp_path):
        """Should not raise an error if the directory already exists."""
        (tmp_path / "background-tasks").mkdir(parents=True)

        with patch("agentic_devtools.task_state.get_state_dir", return_value=tmp_path):
            result = get_background_tasks_dir()

        assert result.exists()
