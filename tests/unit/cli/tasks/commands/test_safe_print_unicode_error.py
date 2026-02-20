"""
Tests for CLI task monitoring commands.

Tests the task monitoring CLI commands that use the actual task_state API:
- BackgroundTask.create + add_task (not create_task)
- update_task (not update_task_status)
- get_background_tasks (returns list, not dict)
- task.id (not task.task_id)
- task.start_time (not task.created_at)
"""

from unittest.mock import patch

import pytest

from agdt_ai_helpers.task_state import (
    BackgroundTask,
    add_task,
)


@pytest.fixture
def mock_state_dir(tmp_path):
    """Fixture to mock the state directory."""
    # Patch get_state_dir in the state module (where it's defined)
    with patch("agdt_ai_helpers.state.get_state_dir", return_value=tmp_path):
        yield tmp_path


def _create_and_add_task(command: str) -> BackgroundTask:
    """Helper to create and add a task using the real API."""
    task = BackgroundTask.create(command=command)
    add_task(task)
    return task


class TestSafePrintUnicodeError:
    """Tests for _safe_print with UnicodeEncodeError handling."""

    def test_safe_print_replaces_emoji_on_unicode_error(self, capsys):
        """Test that emoji is replaced when UnicodeEncodeError occurs."""
        from agdt_ai_helpers.cli.tasks.commands import _safe_print

        # We need to simulate a UnicodeEncodeError on the first print call
        call_count = [0]
        original_print = print

        def mock_print(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call raises UnicodeEncodeError
                raise UnicodeEncodeError("codec", "", 0, 1, "mock error")
            # Subsequent calls succeed
            original_print(*args, **kwargs)

        with patch("builtins.print", side_effect=mock_print):
            _safe_print("Status: ✅ OK")

        # The function should have made a second print call with replaced emoji
        assert call_count[0] == 2
