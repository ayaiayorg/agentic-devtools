"""
Tests for task_state module.
"""

from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from agentic_devtools.task_state import (
    BackgroundTask,
    TaskStatus,
    _sort_tasks,
    add_task,
    get_active_tasks,
    get_background_tasks,
    get_failed_most_recent_per_command,
    get_most_recent_tasks_per_command,
    get_task_by_id,
    get_tasks_by_status,
    remove_task,
    update_task,
)


class TestAddTask:
    """Tests for add_task function."""

    def test_add_task_persists(self, tmp_path):
        """Test add_task persists task to state."""
        state_file = tmp_path / "state.json"
        state_file.write_text("{}")

        with patch("agentic_devtools.task_state.load_state") as mock_load, patch(
            "agentic_devtools.task_state.save_state"
        ) as mock_save, patch("agentic_devtools.task_state._append_to_all_tasks"):
            mock_load.return_value = {}

            task = BackgroundTask.create(command="agdt-test-command")
            add_task(task, use_locking=False)

            # Verify save was called
            mock_save.assert_called_once()
            saved_state = mock_save.call_args[0][0]
            assert "background" in saved_state
            assert "recentTasks" in saved_state["background"]
            assert len(saved_state["background"]["recentTasks"]) == 1
