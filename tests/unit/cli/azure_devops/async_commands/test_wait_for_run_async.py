"""Tests for wait_for_run_async function."""

from agentic_devtools.cli.azure_devops.async_commands import wait_for_run_async


class TestWaitForRunAsync:
    """Tests for wait_for_run_async function."""

    def test_function_exists(self):
        """Verify wait_for_run_async is importable and callable."""
        assert callable(wait_for_run_async)
