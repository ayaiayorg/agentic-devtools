"""Tests for add_pull_request_comment_async_cli function."""

from agentic_devtools.cli.azure_devops.async_commands import add_pull_request_comment_async_cli


class TestAddPullRequestCommentAsyncCli:
    """Tests for add_pull_request_comment_async_cli function."""

    def test_function_exists(self):
        """Verify add_pull_request_comment_async_cli is importable and callable."""
        assert callable(add_pull_request_comment_async_cli)
