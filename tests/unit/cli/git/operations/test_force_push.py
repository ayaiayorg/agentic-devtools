"""Tests for agentic_devtools.cli.git.operations.force_push."""

from agentic_devtools.cli.git import operations


class TestForcePush:
    """Tests for force_push function."""

    def test_force_push(self, mock_run_safe):
        """Test force push with lease."""
        operations.force_push(dry_run=False)
        mock_run_safe.assert_called_once()
        cmd = mock_run_safe.call_args[0][0]
        assert cmd == ["git", "push", "--force-with-lease"]

    def test_force_push_dry_run(self, mock_run_safe, capsys):
        """Test dry run doesn't execute."""
        operations.force_push(dry_run=True)
        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
