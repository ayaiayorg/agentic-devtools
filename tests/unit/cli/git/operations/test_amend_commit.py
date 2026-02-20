"""Tests for agentic_devtools.cli.git.operations.amend_commit."""

from agentic_devtools.cli.git import operations


class TestAmendCommit:
    """Tests for amend_commit function."""

    def test_amend_commit_uses_temp_file(self, mock_run_safe):
        """Test amending a commit uses temp file with -F flag."""
        operations.amend_commit("Test message", dry_run=False)

        mock_run_safe.assert_called_once()
        cmd = mock_run_safe.call_args[0][0]
        assert cmd[0:3] == ["git", "commit", "--amend"]
        assert "-F" in cmd

    def test_amend_commit_dry_run(self, mock_run_safe, capsys):
        """Test dry run shows message."""
        operations.amend_commit("Test message", dry_run=True)
        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Test message" in captured.out
