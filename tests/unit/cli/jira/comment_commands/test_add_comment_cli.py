"""Tests for add_comment_cli function."""

from agentic_devtools.cli.jira.comment_commands import add_comment_cli


class TestAddCommentCli:
    """Tests for add_comment_cli function."""

    def test_function_exists(self):
        """Verify add_comment_cli is importable and callable."""
        assert callable(add_comment_cli)
