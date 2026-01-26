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


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_status_values(self):
        """Test TaskStatus enum has expected values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"

    def test_status_from_string(self):
        """Test creating TaskStatus from string value."""
        assert TaskStatus("pending") == TaskStatus.PENDING
        assert TaskStatus("running") == TaskStatus.RUNNING
        assert TaskStatus("completed") == TaskStatus.COMPLETED
        assert TaskStatus("failed") == TaskStatus.FAILED


class TestBackgroundTask:
    """Tests for BackgroundTask dataclass."""

    def test_create_task_via_factory(self):
        """Test creating a BackgroundTask via factory method."""
        task = BackgroundTask.create(
            command="dfly-test-cmd",
            log_file=Path("/path/to/log.txt"),
            args={"key": "value"},
        )
        assert task.command == "dfly-test-cmd"
        assert task.status == TaskStatus.PENDING
        # Path gets normalized by str(), so check it ends with the filename
        assert task.log_file is not None
        assert task.log_file.endswith("log.txt")
        assert task.args == {"key": "value"}
        assert task.end_time is None
        assert task.exit_code is None
        # ID should be a UUID
        assert len(task.id) == 36

    def test_create_task_dataclass_directly(self):
        """Test creating a BackgroundTask directly."""
        task = BackgroundTask(
            id="test-123",
            command="dfly-test-cmd",
            status=TaskStatus.PENDING,
            start_time="2024-01-01T00:00:00+00:00",
            log_file="/path/to/log.txt",
        )
        assert task.id == "test-123"
        assert task.command == "dfly-test-cmd"
        assert task.status == TaskStatus.PENDING
        assert task.log_file == "/path/to/log.txt"
        assert task.end_time is None
        assert task.exit_code is None

    def test_task_to_dict(self):
        """Test converting task to dictionary."""
        task = BackgroundTask(
            id="test-456",
            command="dfly-another-cmd",
            status=TaskStatus.RUNNING,
            start_time="2024-01-01T12:00:00+00:00",
            log_file="/tmp/log.txt",
        )
        task_dict = task.to_dict()

        assert task_dict["id"] == "test-456"
        assert task_dict["command"] == "dfly-another-cmd"
        assert task_dict["status"] == "running"
        assert task_dict["logFile"] == "/tmp/log.txt"
        assert task_dict["startTime"] == "2024-01-01T12:00:00+00:00"

    def test_task_from_dict(self):
        """Test creating task from dictionary."""
        data = {
            "id": "from-dict-789",
            "command": "dfly-cmd",
            "status": "completed",
            "startTime": "2024-01-01T00:00:00+00:00",
            "logFile": "/log.txt",
            "endTime": "2024-01-01T00:01:00+00:00",
            "exitCode": 0,
        }
        task = BackgroundTask.from_dict(data)

        assert task.id == "from-dict-789"
        assert task.status == TaskStatus.COMPLETED
        assert task.exit_code == 0
        assert task.end_time == "2024-01-01T00:01:00+00:00"

    def test_task_roundtrip(self):
        """Test task survives dict roundtrip."""
        original = BackgroundTask(
            id="roundtrip-test",
            command="dfly-cmd",
            status=TaskStatus.FAILED,
            start_time="2024-06-15T10:30:00+00:00",
            log_file="/var/log/task.log",
            end_time="2024-06-15T10:31:00+00:00",
            exit_code=1,
        )
        restored = BackgroundTask.from_dict(original.to_dict())

        assert restored.id == original.id
        assert restored.command == original.command
        assert restored.status == original.status
        assert restored.exit_code == original.exit_code

    def test_mark_running(self):
        """Test marking task as running."""
        task = BackgroundTask.create(command="test")
        assert task.status == TaskStatus.PENDING
        task.mark_running()
        assert task.status == TaskStatus.RUNNING

    def test_mark_completed(self):
        """Test marking task as completed."""
        task = BackgroundTask.create(command="test")
        task.mark_completed(exit_code=0)
        assert task.status == TaskStatus.COMPLETED
        assert task.exit_code == 0
        assert task.end_time is not None

    def test_mark_failed(self):
        """Test marking task as failed."""
        task = BackgroundTask.create(command="test")
        task.mark_failed(exit_code=1, error_message="Something went wrong")
        assert task.status == TaskStatus.FAILED
        assert task.exit_code == 1
        assert task.error_message == "Something went wrong"
        assert task.end_time is not None

    def test_is_terminal(self):
        """Test is_terminal for various statuses."""
        task = BackgroundTask.create(command="test")
        assert not task.is_terminal()

        task.mark_running()
        assert not task.is_terminal()

        task.mark_completed()
        assert task.is_terminal()

        task2 = BackgroundTask.create(command="test2")
        task2.mark_failed()
        assert task2.is_terminal()

    def test_is_recent_unfinished(self):
        """Test is_recent returns True for unfinished tasks."""
        task = BackgroundTask.create(command="test")
        assert task.is_recent()

        task.mark_running()
        assert task.is_recent()

    def test_is_recent_just_finished(self):
        """Test is_recent returns True for just-finished tasks."""
        task = BackgroundTask.create(command="test")
        task.mark_completed()
        # Task just finished, should still be recent
        assert task.is_recent()


class TestDurationSeconds:
    """Tests for BackgroundTask.duration_seconds method."""

    def test_completed_task_returns_duration(self):
        """Should return duration for completed task with valid timestamps."""
        task = BackgroundTask(
            id="test",
            command="test",
            status=TaskStatus.COMPLETED,
            start_time="2024-01-01T10:00:00+00:00",
            end_time="2024-01-01T10:05:30+00:00",
        )
        duration = task.duration_seconds()
        assert duration == 5 * 60 + 30  # 5 minutes 30 seconds

    def test_pending_task_returns_none(self):
        """Should return None for pending task without end_time."""
        task = BackgroundTask(
            id="test",
            command="test",
            status=TaskStatus.PENDING,
            start_time="2024-01-01T10:00:00+00:00",
        )
        assert task.duration_seconds() is None

    def test_running_task_returns_current_duration(self):
        """Should return current duration for running task."""
        from datetime import datetime, timezone

        # Start time = 10 seconds ago
        now = datetime.now(timezone.utc)
        start_time = (now.replace(microsecond=0) - timedelta(seconds=10)).isoformat()
        task = BackgroundTask(
            id="test",
            command="test",
            status=TaskStatus.RUNNING,
            start_time=start_time,
        )
        duration = task.duration_seconds()
        assert duration is not None
        # Duration should be approximately 10 seconds (with some tolerance for test execution)
        assert 9 <= duration <= 15

    def test_running_task_with_invalid_start_time(self):
        """Should return None if start_time cannot be parsed."""
        task = BackgroundTask(
            id="test",
            command="test",
            status=TaskStatus.RUNNING,
            start_time="not-a-valid-timestamp",
        )
        assert task.duration_seconds() is None

    def test_completed_task_with_invalid_timestamps(self):
        """Should return None if timestamps cannot be parsed."""
        task = BackgroundTask(
            id="test",
            command="test",
            status=TaskStatus.COMPLETED,
            start_time="not-a-valid-timestamp",
            end_time="also-not-valid",
        )
        assert task.duration_seconds() is None


class TestSortTasks:
    """Tests for _sort_tasks function."""

    def test_sort_unfinished_before_finished(self):
        """Test unfinished tasks come before finished tasks."""
        finished = BackgroundTask(
            id="finished",
            command="cmd",
            status=TaskStatus.COMPLETED,
            start_time="2024-01-01T00:00:00+00:00",
            end_time="2024-01-01T00:01:00+00:00",
        )
        unfinished = BackgroundTask(
            id="unfinished",
            command="cmd",
            status=TaskStatus.RUNNING,
            start_time="2024-01-01T00:02:00+00:00",
        )

        sorted_tasks = _sort_tasks([finished, unfinished])

        assert sorted_tasks[0].id == "unfinished"
        assert sorted_tasks[1].id == "finished"

    def test_sort_unfinished_by_start_time(self):
        """Test unfinished tasks sorted by start time (earliest first)."""
        task1 = BackgroundTask(
            id="later",
            command="cmd",
            status=TaskStatus.RUNNING,
            start_time="2024-01-01T00:02:00+00:00",
        )
        task2 = BackgroundTask(
            id="earlier",
            command="cmd",
            status=TaskStatus.PENDING,
            start_time="2024-01-01T00:01:00+00:00",
        )

        sorted_tasks = _sort_tasks([task1, task2])

        assert sorted_tasks[0].id == "earlier"
        assert sorted_tasks[1].id == "later"

    def test_sort_finished_by_end_time(self):
        """Test finished tasks sorted by end time (earliest first)."""
        task1 = BackgroundTask(
            id="ended-later",
            command="cmd",
            status=TaskStatus.COMPLETED,
            start_time="2024-01-01T00:00:00+00:00",
            end_time="2024-01-01T00:03:00+00:00",
        )
        task2 = BackgroundTask(
            id="ended-earlier",
            command="cmd",
            status=TaskStatus.COMPLETED,
            start_time="2024-01-01T00:00:00+00:00",
            end_time="2024-01-01T00:01:00+00:00",
        )

        sorted_tasks = _sort_tasks([task1, task2])

        assert sorted_tasks[0].id == "ended-earlier"
        assert sorted_tasks[1].id == "ended-later"

    def test_sort_tasks_with_invalid_start_time(self):
        """Test sorting handles invalid start_time gracefully."""
        task_valid = BackgroundTask(
            id="valid",
            command="cmd",
            status=TaskStatus.RUNNING,
            start_time="2024-01-01T00:01:00+00:00",
        )
        task_invalid = BackgroundTask(
            id="invalid",
            command="cmd",
            status=TaskStatus.RUNNING,
            start_time="not-a-timestamp",
        )

        # Should not raise, invalid dates get min datetime
        sorted_tasks = _sort_tasks([task_valid, task_invalid])
        assert len(sorted_tasks) == 2

    def test_sort_tasks_with_invalid_end_time(self):
        """Test sorting handles invalid end_time gracefully."""
        task_valid = BackgroundTask(
            id="valid",
            command="cmd",
            status=TaskStatus.COMPLETED,
            start_time="2024-01-01T00:01:00+00:00",
            end_time="2024-01-01T00:02:00+00:00",
        )
        task_invalid = BackgroundTask(
            id="invalid",
            command="cmd",
            status=TaskStatus.COMPLETED,
            start_time="2024-01-01T00:01:00+00:00",
            end_time="not-a-timestamp",
        )

        # Should not raise, invalid dates get max datetime
        sorted_tasks = _sort_tasks([task_valid, task_invalid])
        assert len(sorted_tasks) == 2


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

            task = BackgroundTask.create(command="dfly-test-command")
            add_task(task, use_locking=False)

            # Verify save was called
            mock_save.assert_called_once()
            saved_state = mock_save.call_args[0][0]
            assert "background" in saved_state
            assert "recentTasks" in saved_state["background"]
            assert len(saved_state["background"]["recentTasks"]) == 1


class TestGetTaskById:
    """Tests for get_task_by_id function."""

    def test_get_existing_task(self):
        """Test retrieving an existing task."""
        task = BackgroundTask.create(command="dfly-cmd")

        with patch("agentic_devtools.task_state.load_state") as mock_load, patch(
            "agentic_devtools.task_state.get_task_from_all_tasks", return_value=None
        ):
            mock_load.return_value = {"background": {"recentTasks": [task.to_dict()]}}

            retrieved = get_task_by_id(task.id, use_locking=False)

        assert retrieved is not None
        assert retrieved.id == task.id
        assert retrieved.command == task.command

    def test_get_nonexistent_task(self):
        """Test retrieving a non-existent task returns None."""
        with patch("agentic_devtools.task_state.load_state") as mock_load, patch(
            "agentic_devtools.task_state.get_task_from_all_tasks", return_value=None
        ):
            mock_load.return_value = {"background": {"recentTasks": []}}

            result = get_task_by_id("nonexistent-task-id", use_locking=False)

        assert result is None

    def test_get_task_partial_id_match(self):
        """Test retrieving task with partial ID match."""
        task = BackgroundTask(
            id="12345678-1234-1234-1234-123456789abc",
            command="dfly-cmd",
            status=TaskStatus.PENDING,
            start_time="2024-01-01T00:00:00+00:00",
        )

        with patch("agentic_devtools.task_state.load_state") as mock_load, patch(
            "agentic_devtools.task_state.get_task_from_all_tasks", return_value=None
        ):
            mock_load.return_value = {"background": {"recentTasks": [task.to_dict()]}}

            # Should find by first 8 characters
            retrieved = get_task_by_id("12345678", use_locking=False)

        assert retrieved is not None
        assert retrieved.id == task.id


class TestGetBackgroundTasks:
    """Tests for get_background_tasks function."""

    def test_get_all_tasks_empty(self):
        """Test get_background_tasks with no tasks."""
        with patch("agentic_devtools.task_state.load_state") as mock_load:
            mock_load.return_value = {}

            tasks = get_background_tasks(use_locking=False)

        assert tasks == []

    def test_get_all_tasks_multiple(self):
        """Test get_background_tasks returns all tasks."""
        task1 = BackgroundTask.create(command="cmd1")
        task2 = BackgroundTask.create(command="cmd2")
        task3 = BackgroundTask.create(command="cmd3")

        with patch("agentic_devtools.task_state.load_state") as mock_load:
            mock_load.return_value = {"background": {"recentTasks": [t.to_dict() for t in [task1, task2, task3]]}}

            all_tasks = get_background_tasks(use_locking=False)

        assert len(all_tasks) == 3
        task_ids = {t.id for t in all_tasks}
        assert task1.id in task_ids
        assert task2.id in task_ids
        assert task3.id in task_ids


class TestGetMostRecentTasksPerCommand:
    """Tests for get_most_recent_tasks_per_command function."""

    def test_empty_tasks(self):
        """Test with no tasks."""

        with patch("agentic_devtools.task_state.get_recent_tasks", return_value=[]):
            result = get_most_recent_tasks_per_command()

        assert result == {}

    def test_single_task_per_command(self):
        """Test with one task per command."""

        task1 = BackgroundTask.create(command="dfly-git-save-work")
        task2 = BackgroundTask.create(command="dfly-add-jira-comment")

        with patch("agentic_devtools.task_state.get_recent_tasks", return_value=[task1, task2]):
            result = get_most_recent_tasks_per_command()

        assert len(result) == 2
        assert result["dfly-git-save-work"].id == task1.id
        assert result["dfly-add-jira-comment"].id == task2.id

    def test_multiple_tasks_same_command_returns_most_recent(self):
        """Test that most recent task is returned when multiple exist for same command."""

        # Create tasks with different start times
        task1 = BackgroundTask.create(command="dfly-git-save-work")
        task2 = BackgroundTask.create(command="dfly-git-save-work")  # More recent

        # List is already sorted with most recent first (task2 first)
        with patch("agentic_devtools.task_state.get_recent_tasks", return_value=[task2, task1]):
            result = get_most_recent_tasks_per_command()

        assert len(result) == 1
        # task2 should be selected as it appears first (most recent)
        assert result["dfly-git-save-work"].id == task2.id


class TestGetFailedMostRecentPerCommand:
    """Tests for get_failed_most_recent_per_command function."""

    def test_empty_tasks(self):
        """Test with no tasks."""
        from agentic_devtools.task_state import get_failed_most_recent_per_command

        with patch("agentic_devtools.task_state.get_most_recent_tasks_per_command", return_value={}):
            result = get_failed_most_recent_per_command()

        assert result == []

    def test_all_successful(self):
        """Test with all successful tasks."""
        from agentic_devtools.task_state import get_failed_most_recent_per_command

        task1 = BackgroundTask.create(command="dfly-git-save-work")
        task1.mark_completed(exit_code=0)

        with patch(
            "agentic_devtools.task_state.get_most_recent_tasks_per_command",
            return_value={"dfly-git-save-work": task1},
        ):
            result = get_failed_most_recent_per_command()

        assert result == []

    def test_returns_failed_tasks(self):
        """Test that failed tasks are returned."""
        from agentic_devtools.task_state import get_failed_most_recent_per_command

        task1 = BackgroundTask.create(command="dfly-git-save-work")
        task1.mark_failed(exit_code=1)
        task2 = BackgroundTask.create(command="dfly-add-jira-comment")
        task2.mark_completed(exit_code=0)

        with patch(
            "agentic_devtools.task_state.get_most_recent_tasks_per_command",
            return_value={"dfly-git-save-work": task1, "dfly-add-jira-comment": task2},
        ):
            result = get_failed_most_recent_per_command()

        assert len(result) == 1
        assert result[0].id == task1.id

    def test_excludes_specified_task(self):
        """Test that exclude_task_id parameter works."""
        from agentic_devtools.task_state import get_failed_most_recent_per_command

        task1 = BackgroundTask.create(command="dfly-git-save-work")
        task1.mark_failed(exit_code=1)
        task2 = BackgroundTask.create(command="dfly-add-jira-comment")
        task2.mark_failed(exit_code=1)

        with patch(
            "agentic_devtools.task_state.get_most_recent_tasks_per_command",
            return_value={"dfly-git-save-work": task1, "dfly-add-jira-comment": task2},
        ):
            result = get_failed_most_recent_per_command(exclude_task_id=task1.id)

        assert len(result) == 1
        assert result[0].id == task2.id

    def test_exclude_commands_skips_matching_command(self, tmp_path):
        """Test that exclude_commands parameter skips tasks with matching commands.

        This is the bug fix scenario: when a task for dfly-git-save-work succeeds,
        we should not report an older failed dfly-git-save-work task.
        """
        import time

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            # Create an older failed task for dfly-git-save-work
            older_failed = BackgroundTask.create(command="dfly-git-save-work")
            older_failed.mark_running()
            older_failed.mark_failed(exit_code=1)
            add_task(older_failed)

            # Small delay to ensure different timestamps
            time.sleep(0.01)

            # Create a newer successful task for dfly-git-save-work
            newer_success = BackgroundTask.create(command="dfly-git-save-work")
            newer_success.mark_running()
            newer_success.mark_completed(exit_code=0)
            add_task(newer_success)

            # Create a failed task for a different command
            other_failed = BackgroundTask.create(command="dfly-other-cmd")
            other_failed.mark_running()
            other_failed.mark_failed(exit_code=1)
            add_task(other_failed)

            # When excluding the dfly-git-save-work command, we should not see the older failed task
            result = get_failed_most_recent_per_command(
                exclude_task_id=newer_success.id,
                exclude_commands=["dfly-git-save-work"],
            )

            # Should only see the other_failed task, not older_failed
            assert len(result) == 1
            assert result[0].command == "dfly-other-cmd"

    def test_exclude_commands_empty_list(self, tmp_path):
        """Test that empty exclude_commands list has no effect."""
        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            failed_task = BackgroundTask.create(command="dfly-cmd-a")
            failed_task.mark_running()
            failed_task.mark_failed(exit_code=1)
            add_task(failed_task)

            result = get_failed_most_recent_per_command(exclude_commands=[])
            assert len(result) == 1
            assert result[0].command == "dfly-cmd-a"

    def test_exclude_commands_none(self, tmp_path):
        """Test that None exclude_commands has no effect."""
        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            failed_task = BackgroundTask.create(command="dfly-cmd-a")
            failed_task.mark_running()
            failed_task.mark_failed(exit_code=1)
            add_task(failed_task)

            result = get_failed_most_recent_per_command(exclude_commands=None)
            assert len(result) == 1
            assert result[0].command == "dfly-cmd-a"

    def test_exclude_commands_multiple(self, tmp_path):
        """Test excluding multiple commands."""
        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            # Create failed tasks for different commands
            failed_a = BackgroundTask.create(command="dfly-cmd-a")
            failed_a.mark_running()
            failed_a.mark_failed(exit_code=1)
            add_task(failed_a)

            failed_b = BackgroundTask.create(command="dfly-cmd-b")
            failed_b.mark_running()
            failed_b.mark_failed(exit_code=1)
            add_task(failed_b)

            failed_c = BackgroundTask.create(command="dfly-cmd-c")
            failed_c.mark_running()
            failed_c.mark_failed(exit_code=1)
            add_task(failed_c)

            result = get_failed_most_recent_per_command(exclude_commands=["dfly-cmd-a", "dfly-cmd-b"])
            assert len(result) == 1
            assert result[0].command == "dfly-cmd-c"


class TestGetIncompleteMostRecentPerCommand:
    """Tests for get_incomplete_most_recent_per_command function."""

    def test_empty_tasks(self):
        """Test with no tasks."""
        from agentic_devtools.task_state import get_incomplete_most_recent_per_command

        with patch("agentic_devtools.task_state.get_most_recent_tasks_per_command", return_value={}):
            result = get_incomplete_most_recent_per_command()

        assert result == []

    def test_all_complete(self):
        """Test with all completed tasks."""
        from agentic_devtools.task_state import get_incomplete_most_recent_per_command

        task1 = BackgroundTask.create(command="dfly-git-save-work")
        task1.mark_completed(exit_code=0)
        task2 = BackgroundTask.create(command="dfly-add-jira-comment")
        task2.mark_failed(exit_code=1)

        with patch(
            "agentic_devtools.task_state.get_most_recent_tasks_per_command",
            return_value={"dfly-git-save-work": task1, "dfly-add-jira-comment": task2},
        ):
            result = get_incomplete_most_recent_per_command()

        # Both completed and failed are considered "complete"
        assert result == []

    def test_returns_incomplete_tasks(self):
        """Test that incomplete tasks are returned."""
        from agentic_devtools.task_state import get_incomplete_most_recent_per_command

        task1 = BackgroundTask.create(command="dfly-git-save-work")
        task1.mark_running()
        task2 = BackgroundTask.create(command="dfly-add-jira-comment")
        task2.mark_completed(exit_code=0)
        task3 = BackgroundTask.create(command="dfly-create-pr")
        # task3 is pending (default state)

        with patch(
            "agentic_devtools.task_state.get_most_recent_tasks_per_command",
            return_value={
                "dfly-git-save-work": task1,
                "dfly-add-jira-comment": task2,
                "dfly-create-pr": task3,
            },
        ):
            result = get_incomplete_most_recent_per_command()

        assert len(result) == 2
        result_ids = {t.id for t in result}
        assert task1.id in result_ids  # running
        assert task3.id in result_ids  # pending

    def test_excludes_specified_task(self):
        """Test that exclude_task_id parameter works."""
        from agentic_devtools.task_state import get_incomplete_most_recent_per_command

        task1 = BackgroundTask.create(command="dfly-git-save-work")
        task1.mark_running()
        task2 = BackgroundTask.create(command="dfly-add-jira-comment")
        task2.mark_running()

        with patch(
            "agentic_devtools.task_state.get_most_recent_tasks_per_command",
            return_value={"dfly-git-save-work": task1, "dfly-add-jira-comment": task2},
        ):
            result = get_incomplete_most_recent_per_command(exclude_task_id=task1.id)

        assert len(result) == 1
        assert result[0].id == task2.id


class TestUpdateTask:
    """Tests for update_task function."""

    def test_update_existing_task(self):
        """Test updating an existing task."""
        task = BackgroundTask.create(command="cmd")

        with patch("agentic_devtools.task_state.load_state") as mock_load, patch(
            "agentic_devtools.task_state.save_state"
        ) as mock_save, patch("agentic_devtools.task_state._update_task_in_all_tasks"), patch(
            "agentic_devtools.task_state._append_to_all_tasks"
        ):
            mock_load.return_value = {"background": {"recentTasks": [task.to_dict()]}}

            task.mark_running()
            result = update_task(task, use_locking=False)

        assert result is True
        mock_save.assert_called_once()

    def test_update_nonexistent_task(self):
        """Test updating a non-existent task returns False."""
        task = BackgroundTask.create(command="cmd")

        with patch("agentic_devtools.task_state.load_state") as mock_load:
            mock_load.return_value = {"background": {"recentTasks": []}}

            result = update_task(task, use_locking=False)

        assert result is False


class TestRemoveTask:
    """Tests for remove_task function."""

    def test_remove_existing_task(self):
        """Test removing an existing task."""
        task = BackgroundTask.create(command="cmd")

        with patch("agentic_devtools.task_state.load_state") as mock_load, patch(
            "agentic_devtools.task_state.save_state"
        ) as mock_save, patch("agentic_devtools.task_state._load_all_tasks_file", return_value=[]), patch(
            "agentic_devtools.task_state._save_all_tasks_file"
        ):
            mock_load.return_value = {"background": {"recentTasks": [task.to_dict()]}}

            result = remove_task(task.id, use_locking=False)

        assert result is True
        mock_save.assert_called_once()
        saved_state = mock_save.call_args[0][0]
        assert len(saved_state["background"]["recentTasks"]) == 0

    def test_remove_nonexistent_task(self):
        """Test removing a non-existent task returns False."""
        with patch("agentic_devtools.task_state.load_state") as mock_load, patch(
            "agentic_devtools.task_state._load_all_tasks_file", return_value=[]
        ), patch("agentic_devtools.task_state._save_all_tasks_file"):
            mock_load.return_value = {"background": {"recentTasks": []}}

            result = remove_task("nonexistent-id", use_locking=False)

        assert result is False

    def test_remove_preserves_other_tasks(self):
        """Test removing one task preserves others."""
        task1 = BackgroundTask.create(command="cmd1")
        task2 = BackgroundTask.create(command="cmd2")

        with patch("agentic_devtools.task_state.load_state") as mock_load, patch(
            "agentic_devtools.task_state.save_state"
        ) as mock_save, patch("agentic_devtools.task_state._load_all_tasks_file", return_value=[]), patch(
            "agentic_devtools.task_state._save_all_tasks_file"
        ):
            mock_load.return_value = {"background": {"recentTasks": [task1.to_dict(), task2.to_dict()]}}

            remove_task(task1.id, use_locking=False)

        saved_state = mock_save.call_args[0][0]
        assert len(saved_state["background"]["recentTasks"]) == 1
        assert saved_state["background"]["recentTasks"][0]["id"] == task2.id


class TestGetTasksByStatus:
    """Tests for get_tasks_by_status function."""

    def test_filter_by_status(self):
        """Test filtering tasks by status."""
        task1 = BackgroundTask.create(command="cmd1")
        task2 = BackgroundTask.create(command="cmd2")
        task2.mark_running()
        task3 = BackgroundTask.create(command="cmd3")
        task3.mark_completed()

        with patch("agentic_devtools.task_state.load_state") as mock_load:
            mock_load.return_value = {"background": {"recentTasks": [t.to_dict() for t in [task1, task2, task3]]}}

            pending = get_tasks_by_status(TaskStatus.PENDING, use_locking=False)
            running = get_tasks_by_status(TaskStatus.RUNNING, use_locking=False)
            completed = get_tasks_by_status(TaskStatus.COMPLETED, use_locking=False)

        assert len(pending) == 1
        assert pending[0].id == task1.id
        assert len(running) == 1
        assert running[0].id == task2.id
        assert len(completed) == 1
        assert completed[0].id == task3.id


class TestGetActiveTasks:
    """Tests for get_active_tasks function."""

    def test_get_active_tasks(self):
        """Test getting active (pending/running) tasks."""
        task1 = BackgroundTask.create(command="cmd1")  # pending
        task2 = BackgroundTask.create(command="cmd2")
        task2.mark_running()
        task3 = BackgroundTask.create(command="cmd3")
        task3.mark_completed()

        with patch("agentic_devtools.task_state.load_state") as mock_load:
            mock_load.return_value = {"background": {"recentTasks": [t.to_dict() for t in [task1, task2, task3]]}}

            active = get_active_tasks(use_locking=False)

        assert len(active) == 2
        active_ids = {t.id for t in active}
        assert task1.id in active_ids
        assert task2.id in active_ids
        assert task3.id not in active_ids


class TestTaskLifecycle:
    """Integration tests for full task lifecycle."""

    def test_full_lifecycle_success(self):
        """Test complete lifecycle: create -> running -> completed."""
        task = BackgroundTask.create(command="dfly-test-cmd")
        assert task.status == TaskStatus.PENDING

        # Start running
        task.mark_running()
        assert task.status == TaskStatus.RUNNING

        # Complete successfully
        task.mark_completed(exit_code=0)
        assert task.status == TaskStatus.COMPLETED
        assert task.exit_code == 0
        assert task.end_time is not None

    def test_full_lifecycle_failure(self):
        """Test complete lifecycle: create -> running -> failed."""
        task = BackgroundTask.create(command="dfly-failing-cmd")

        task.mark_running()
        task.mark_failed(exit_code=1, error_message="Process crashed")

        assert task.status == TaskStatus.FAILED
        assert task.exit_code == 1
        assert task.error_message == "Process crashed"


class TestGetOtherIncompleteTasks:
    """Tests for get_other_incomplete_tasks function."""

    def test_returns_empty_when_no_tasks(self, tmp_path):
        """Test returns empty list when no tasks exist."""
        from agentic_devtools.task_state import get_other_incomplete_tasks

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            result = get_other_incomplete_tasks("some-task-id")
            assert result == []

    def test_excludes_current_task_id(self, tmp_path):
        """Test excludes the specified task ID from results."""
        from agentic_devtools.task_state import get_other_incomplete_tasks

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            task1 = BackgroundTask.create(command="cmd1")
            task1.mark_running()
            add_task(task1)

            task2 = BackgroundTask.create(command="cmd2")
            task2.mark_running()
            add_task(task2)

            # Get incomplete tasks excluding task1
            result = get_other_incomplete_tasks(task1.id)

            assert len(result) == 1
            assert result[0].id == task2.id

    def test_excludes_completed_tasks(self, tmp_path):
        """Test excludes completed tasks from results."""
        from agentic_devtools.task_state import get_other_incomplete_tasks

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            running_task = BackgroundTask.create(command="running")
            running_task.mark_running()
            add_task(running_task)

            completed_task = BackgroundTask.create(command="completed")
            completed_task.mark_running()
            completed_task.mark_completed(exit_code=0)
            add_task(completed_task)

            # Get incomplete tasks excluding a fake ID
            result = get_other_incomplete_tasks("fake-id")

            assert len(result) == 1
            assert result[0].id == running_task.id

    def test_excludes_failed_tasks(self, tmp_path):
        """Test excludes failed tasks from results."""
        from agentic_devtools.task_state import get_other_incomplete_tasks

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            running_task = BackgroundTask.create(command="running")
            running_task.mark_running()
            add_task(running_task)

            failed_task = BackgroundTask.create(command="failed")
            failed_task.mark_running()
            failed_task.mark_failed(exit_code=1, error_message="Error")
            add_task(failed_task)

            result = get_other_incomplete_tasks("fake-id")

            assert len(result) == 1
            assert result[0].id == running_task.id


class TestPrintTaskTrackingInfo:
    """Tests for print_task_tracking_info function."""

    def test_sets_task_id_in_state(self, tmp_path, capsys):
        """Test that task_id is automatically set in state."""
        from agentic_devtools.state import get_value
        from agentic_devtools.task_state import print_task_tracking_info

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            task = BackgroundTask.create(command="dfly-test-cmd")
            print_task_tracking_info(task, "Testing task")

            assert get_value("background.task_id") == task.id

    def test_prints_task_started_message(self, tmp_path, capsys):
        """Test that task started message is printed."""
        from agentic_devtools.task_state import print_task_tracking_info

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            task = BackgroundTask.create(command="dfly-test-cmd")
            print_task_tracking_info(task, "Testing task")

            captured = capsys.readouterr()
            assert "Background task started" in captured.out
            assert "dfly-test-cmd" in captured.out
            assert task.id in captured.out
            assert "task_id automatically set" in captured.out

    def test_prints_action_description(self, tmp_path, capsys):
        """Test that action description is printed."""
        from agentic_devtools.task_state import print_task_tracking_info

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            task = BackgroundTask.create(command="dfly-test-cmd")
            print_task_tracking_info(task, "Adding comment to DFLY-1234")

            captured = capsys.readouterr()
            assert "Adding comment to DFLY-1234..." in captured.out

    def test_prints_tracking_commands(self, tmp_path, capsys):
        """Test that tracking commands are printed."""
        from agentic_devtools.task_state import print_task_tracking_info

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            task = BackgroundTask.create(command="dfly-test-cmd")
            print_task_tracking_info(task, "Testing")

            captured = capsys.readouterr()
            # Simplified output now just shows dfly-task-wait
            assert "dfly-task-wait" in captured.out
            # Should NOT show the verbose commands anymore
            assert '--id "<task-id>"' not in captured.out

    def test_shows_other_incomplete_tasks(self, tmp_path, capsys):
        """Test that simplified output does NOT show other incomplete tasks (moved to task_wait)."""
        from agentic_devtools.task_state import print_task_tracking_info

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            # Add a running task first
            other_task = BackgroundTask.create(command="dfly-other-cmd")
            other_task.mark_running()
            add_task(other_task)

            # Now print info for a new task
            new_task = BackgroundTask.create(command="dfly-new-cmd")
            print_task_tracking_info(new_task, "Testing")

            captured = capsys.readouterr()
            # Other tasks are now NOT shown in print_task_tracking_info
            # They are handled by task_wait instead
            assert "Other recent incomplete background tasks:" not in captured.out
            # Just shows simple dfly-task-wait instruction
            assert "dfly-task-wait" in captured.out
