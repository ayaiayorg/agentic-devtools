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

    def test_amend_commit_with_old_title_prints_title_change(self, mock_run_safe, capsys):
        """Test that passing old_title prints a before/after title diff."""
        operations.amend_commit("feat(#42): new title\n\nbody", dry_run=False, old_title="feat(#42): old title")
        captured = capsys.readouterr()
        assert "feat(#42): old title" in captured.out
        assert "feat(#42): new title" in captured.out

    def test_amend_commit_without_old_title_no_title_change(self, mock_run_safe, capsys):
        """Test that omitting old_title does not print title change."""
        operations.amend_commit("feat(#42): title\n\nbody", dry_run=False)
        captured = capsys.readouterr()
        assert "Title Change" not in captured.out
