"""Tests for reply_to_pull_request_thread_async_cli function."""

from agentic_devtools.cli.azure_devops.async_commands import reply_to_pull_request_thread_async_cli


class TestReplyToPullRequestThreadAsyncCli:
    """Tests for reply_to_pull_request_thread_async_cli function."""

    def test_function_exists(self):
        """Verify reply_to_pull_request_thread_async_cli is importable and callable."""
        assert callable(reply_to_pull_request_thread_async_cli)
