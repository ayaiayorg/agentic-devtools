"""Tests for task_state module."""

from agentic_devtools.task_state import cleanup_expired_tasks


class TestCleanupExpiredTasks:
    """Tests for cleanup_expired_tasks function."""

    def test_function_exists(self):
        """Verify cleanup_expired_tasks is importable and callable."""
        assert callable(cleanup_expired_tasks)
