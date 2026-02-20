"""Tests for agentic_devtools.cli.git.operations.get_last_commit_message."""

from agentic_devtools.cli.git.operations import get_last_commit_message  # noqa: F401


class TestGetLastCommitMessage:
    """Tests for get_last_commit_message function."""

    def test_importable(self):
        """Test get_last_commit_message can be imported and is callable."""
        assert callable(get_last_commit_message)
