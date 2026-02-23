"""Tests for agentic_devtools.cli.git.operations.stage_changes."""

from agentic_devtools.cli.git import operations


class TestStageChanges:
    """Tests for stage_changes function."""

    def test_stage_changes(self, mock_run_safe):
        """Test staging all changes."""
        operations.stage_changes(dry_run=False)
        mock_run_safe.assert_called_once()
        cmd = mock_run_safe.call_args[0][0]
        assert cmd == ["git", "add", "."]

    def test_stage_changes_dry_run(self, mock_run_safe, capsys):
        """Test dry run doesn't execute."""
        operations.stage_changes(dry_run=True)
        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
