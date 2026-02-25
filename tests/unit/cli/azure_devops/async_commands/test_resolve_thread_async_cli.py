"""Tests for resolve_thread_async_cli function."""

from agentic_devtools.cli.azure_devops.async_commands import resolve_thread_async_cli


class TestResolveThreadAsyncCli:
    """Tests for resolve_thread_async_cli function."""

    def test_function_exists(self):
        """Verify resolve_thread_async_cli is importable and callable."""
        assert callable(resolve_thread_async_cli)
