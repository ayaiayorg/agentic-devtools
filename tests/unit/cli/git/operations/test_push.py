"""Tests for agentic_devtools.cli.git.operations.push."""

from agentic_devtools.cli.git import operations


class TestPush:
    """Tests for push function."""

    def test_push(self, mock_run_safe):
        """Test regular push."""
        operations.push(dry_run=False)
        mock_run_safe.assert_called_once()
        cmd = mock_run_safe.call_args[0][0]
        assert cmd == ["git", "push"]

    def test_push_dry_run(self, mock_run_safe, capsys):
        """Test dry run doesn't execute."""
        operations.push(dry_run=True)
        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
