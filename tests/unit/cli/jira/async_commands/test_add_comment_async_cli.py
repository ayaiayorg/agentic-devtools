"""Tests for add_comment_async_cli function."""

from agentic_devtools.cli.jira.async_commands import add_comment_async_cli


class TestAddCommentAsyncCli:
    """Tests for add_comment_async_cli function."""

    def test_function_exists(self):
        """Verify add_comment_async_cli is importable and callable."""
        assert callable(add_comment_async_cli)
