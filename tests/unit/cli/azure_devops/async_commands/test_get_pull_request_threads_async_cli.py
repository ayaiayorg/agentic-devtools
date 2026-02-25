"""Tests for get_pull_request_threads_async_cli function."""

from agentic_devtools.cli.azure_devops.async_commands import get_pull_request_threads_async_cli


class TestGetPullRequestThreadsAsyncCli:
    """Tests for get_pull_request_threads_async_cli function."""

    def test_function_exists(self):
        """Verify get_pull_request_threads_async_cli is importable and callable."""
        assert callable(get_pull_request_threads_async_cli)
