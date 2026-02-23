"""Tests for agentic_devtools.cli.git.operations.stage_changes."""

from agentic_devtools.cli.git import operations


class TestStageChanges:
    """Tests for stage_changes function."""

    def test_stage_changes(self, mock_run_safe):
        """Test staging all changes calls git add . then unstages excluded files."""
        operations.stage_changes(dry_run=False)
        calls = mock_run_safe.call_args_list
        # First call is git add .
        assert calls[0][0][0] == ["git", "add", "."]
        # Subsequent calls are git reset HEAD -- <excluded_file> for each excluded file
        for i, excluded in enumerate(operations.STAGE_EXCLUDE_FILES):
            assert calls[i + 1][0][0] == ["git", "reset", "HEAD", "--", excluded]

    def test_stage_changes_dry_run(self, mock_run_safe, capsys):
        """Test dry run doesn't execute."""
        operations.stage_changes(dry_run=True)
        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out

    def test_stage_changes_dry_run_mentions_excluded_files(self, mock_run_safe, capsys):
        """Test dry run output mentions each excluded file."""
        operations.stage_changes(dry_run=True)
        captured = capsys.readouterr()
        for excluded in operations.STAGE_EXCLUDE_FILES:
            assert excluded in captured.out

    def test_stage_changes_version_file_excluded(self, mock_run_safe):
        """Test that _version.py is in the exclude list."""
        assert "agentic_devtools/_version.py" in operations.STAGE_EXCLUDE_FILES
