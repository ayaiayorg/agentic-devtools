"""Tests for get_task_from_all_tasks function."""

import json
from unittest.mock import patch

from agentic_devtools.task_state import BackgroundTask, get_task_from_all_tasks


class TestGetTaskFromAllTasks:
    """Tests for get_task_from_all_tasks function."""

    def test_returns_none_when_file_does_not_exist(self, tmp_path):
        """Should return None when the all-tasks file is missing."""
        with patch(
            "agentic_devtools.task_state.get_all_tasks_file_path",
            return_value=tmp_path / "nonexistent.json",
        ):
            result = get_task_from_all_tasks("some-task-id")

        assert result is None

    def test_returns_task_by_exact_id(self, tmp_path):
        """Should return the task matching the given ID."""
        task = BackgroundTask.create(command="agdt-test")
        tasks_file = tmp_path / "all-background-tasks.json"
        tasks_file.write_text(json.dumps([task.to_dict()]))

        with patch(
            "agentic_devtools.task_state.get_all_tasks_file_path",
            return_value=tasks_file,
        ):
            result = get_task_from_all_tasks(task.id)

        assert result is not None
        assert result.id == task.id
        assert result.command == "agdt-test"

    def test_returns_none_for_unknown_id(self, tmp_path):
        """Should return None when no task matches the given ID."""
        task = BackgroundTask.create(command="agdt-test")
        tasks_file = tmp_path / "all-background-tasks.json"
        tasks_file.write_text(json.dumps([task.to_dict()]))

        with patch(
            "agentic_devtools.task_state.get_all_tasks_file_path",
            return_value=tasks_file,
        ):
            result = get_task_from_all_tasks("00000000-0000-0000-0000-000000000000")

        assert result is None
