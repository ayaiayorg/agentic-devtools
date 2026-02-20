"""Tests for agentic_devtools.cli.git.operations.rebase_onto_main."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git import operations


class TestRebaseOntoMain:
    """Tests for rebase_onto_main function."""

    def test_no_rebase_needed(self, mock_run_safe):
        """Test returns NO_REBASE_NEEDED when already up to date."""
        with patch.object(operations, "get_commits_behind_main", return_value=0):
            result = operations.rebase_onto_main(dry_run=False)
            assert result.status == operations.RebaseResult.NO_REBASE_NEEDED
            assert result.is_success

    def test_dry_run(self, mock_run_safe, capsys):
        """Test dry run shows what would happen."""
        with patch.object(operations, "get_commits_behind_main", return_value=5):
            result = operations.rebase_onto_main(dry_run=True)
            assert result.is_success
            captured = capsys.readouterr()
            assert "[DRY RUN]" in captured.out
            assert "5 commits behind" in captured.out

    def test_rebase_success(self, mock_run_safe):
        """Test successful rebase."""
        with patch.object(operations, "get_commits_behind_main", return_value=3):
            with patch.object(operations, "run_git") as mock_run_git:
                mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")
                result = operations.rebase_onto_main(dry_run=False)
                assert result.status == operations.RebaseResult.SUCCESS
                assert result.is_success

    def test_rebase_conflict(self, mock_run_safe):
        """Test rebase with conflicts."""
        with patch.object(operations, "get_commits_behind_main", return_value=3):
            with patch.object(operations, "run_git") as mock_run_git:
                mock_run_git.side_effect = [
                    MagicMock(returncode=1, stdout="", stderr="CONFLICT"),
                    MagicMock(returncode=0, stdout="", stderr=""),
                ]
                result = operations.rebase_onto_main(dry_run=False)
                assert result.status == operations.RebaseResult.CONFLICT
                assert result.needs_manual_resolution

    def test_rebase_conflict_abort_fails(self, mock_run_safe):
        """Test rebase conflict when abort also fails."""
        with patch.object(operations, "get_commits_behind_main", return_value=3):
            with patch.object(operations, "run_git") as mock_run_git:
                mock_run_git.side_effect = [
                    MagicMock(returncode=1, stdout="conflict", stderr=""),
                    MagicMock(returncode=1, stdout="", stderr="abort failed"),
                ]
                result = operations.rebase_onto_main(dry_run=False)
                assert result.status == operations.RebaseResult.ERROR
                assert "abort" in result.message.lower()

    def test_rebase_other_error(self, mock_run_safe):
        """Test rebase with non-conflict error."""
        with patch.object(operations, "get_commits_behind_main", return_value=3):
            with patch.object(operations, "run_git") as mock_run_git:
                mock_run_git.side_effect = [
                    MagicMock(returncode=1, stdout="", stderr="some other error"),
                    MagicMock(returncode=0, stdout="", stderr=""),
                ]
                result = operations.rebase_onto_main(dry_run=False)
                assert result.status == operations.RebaseResult.ERROR
