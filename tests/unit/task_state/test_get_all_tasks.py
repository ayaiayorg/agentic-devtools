"""Tests for get_all_tasks function."""

import json

from unittest.mock import patch

from agentic_devtools.task_state import BackgroundTask, get_all_tasks


class TestGetAllTasks:
    """Tests for get_all_tasks function."""

    def test_returns_empty_when_no_file(self, tmp_path):
        """Should return empty list when the all-tasks file does not exist."""
        with patch(
            "agentic_devtools.task_state.get_all_tasks_file_path",
            return_value=tmp_path / "nonexistent.json",
        ):
            result = get_all_tasks()

        assert result == []

    def test_returns_tasks_from_file(self, tmp_path):
        """Should return tasks loaded from the all-background-tasks.json file."""
        task = BackgroundTask.create(command="agdt-test")
        tasks_file = tmp_path / "all-background-tasks.json"
        tasks_file.write_text(json.dumps([task.to_dict()]))

        with patch(
            "agentic_devtools.task_state.get_all_tasks_file_path",
            return_value=tasks_file,
        ):
            result = get_all_tasks()

        assert len(result) == 1
        assert result[0].id == task.id

    def test_returns_multiple_tasks(self, tmp_path):
        """Should return all tasks stored in the file."""
        task1 = BackgroundTask.create(command="agdt-test")
        task2 = BackgroundTask.create(command="agdt-test-quick")
        tasks_file = tmp_path / "all-background-tasks.json"
        tasks_file.write_text(json.dumps([task1.to_dict(), task2.to_dict()]))

        with patch(
            "agentic_devtools.task_state.get_all_tasks_file_path",
            return_value=tasks_file,
        ):
            result = get_all_tasks()

        assert len(result) == 2
        ids = {t.id for t in result}
        assert task1.id in ids
        assert task2.id in ids
