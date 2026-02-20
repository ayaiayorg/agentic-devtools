"""Tests for agentic_devtools.cli.git.operations.create_commit."""

from agentic_devtools.cli.git import operations


class TestCreateCommit:
    """Tests for create_commit function."""

    def test_create_commit(self, mock_run_safe):
        """Test creating a commit uses temp file for message."""
        operations.create_commit("Test message", dry_run=False)
        mock_run_safe.assert_called_once()
        cmd = mock_run_safe.call_args[0][0]
        assert cmd[0:3] == ["git", "commit", "-F"]
        assert len(cmd) == 4

    def test_create_commit_dry_run(self, mock_run_safe, capsys):
        """Test dry run shows message."""
        operations.create_commit("Test message", dry_run=True)
        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Test message" in captured.out

    def test_create_commit_multiline(self, mock_run_safe):
        """Test multiline commit message uses temp file."""
        message = "Title\n\n- Change 1\n- Change 2"
        operations.create_commit(message, dry_run=False)
        cmd = mock_run_safe.call_args[0][0]
        assert cmd[0:2] == ["git", "commit"]
        assert "-F" in cmd
