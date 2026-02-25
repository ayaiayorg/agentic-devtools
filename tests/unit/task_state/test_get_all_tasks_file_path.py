"""Tests for get_all_tasks_file_path function."""

from unittest.mock import patch

from agentic_devtools.task_state import get_all_tasks_file_path


class TestGetAllTasksFilePath:
    """Tests for get_all_tasks_file_path function."""

    def test_returns_json_file_under_background_tasks_dir(self, tmp_path):
        """Should return all-background-tasks.json under background-tasks dir."""
        bg_dir = tmp_path / "background-tasks"
        bg_dir.mkdir(parents=True)

        with patch("agentic_devtools.task_state.get_background_tasks_dir", return_value=bg_dir):
            result = get_all_tasks_file_path()

        assert result == bg_dir / "all-background-tasks.json"

    def test_returns_path_object(self, tmp_path):
        """Should return a Path object."""
        from pathlib import Path

        bg_dir = tmp_path / "background-tasks"
        bg_dir.mkdir(parents=True)

        with patch("agentic_devtools.task_state.get_background_tasks_dir", return_value=bg_dir):
            result = get_all_tasks_file_path()

        assert isinstance(result, Path)

    def test_file_name_is_correct(self, tmp_path):
        """The filename should be all-background-tasks.json."""
        bg_dir = tmp_path / "background-tasks"
        bg_dir.mkdir(parents=True)

        with patch("agentic_devtools.task_state.get_background_tasks_dir", return_value=bg_dir):
            result = get_all_tasks_file_path()

        assert result.name == "all-background-tasks.json"
