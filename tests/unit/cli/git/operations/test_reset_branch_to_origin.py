"""Tests for agentic_devtools.cli.git.operations.reset_branch_to_origin."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.git import operations


class TestResetBranchToOrigin:
    """Tests for reset_branch_to_origin function."""

    def test_reset_branch_to_origin_success(self, mock_run_safe):
        """Test successful branch reset when no unpushed commits."""
        with patch.object(operations, "run_git") as mock_run_git:
            # First call: rev-list ahead check returns 0
            # Second call: reset --hard succeeds
            mock_run_git.side_effect = [
                MagicMock(returncode=0, stdout="0\n", stderr=""),
                MagicMock(returncode=0, stdout="", stderr=""),
            ]

            result = operations.reset_branch_to_origin("feature/test")

            assert result is True
            assert mock_run_git.call_count == 2
            reset_call = mock_run_git.call_args_list[1]
            assert "reset" in reset_call[0]
            assert "--hard" in reset_call[0]
            assert "origin/feature/test" in reset_call[0]

    def test_reset_branch_to_origin_failure(self, mock_run_safe):
        """Test branch reset failure returns False."""
        with patch.object(operations, "run_git") as mock_run_git:
            # rev-list returns 0 ahead, reset fails
            mock_run_git.side_effect = [
                MagicMock(returncode=0, stdout="0\n", stderr=""),
                MagicMock(returncode=1, stdout="", stderr="error"),
            ]

            result = operations.reset_branch_to_origin("nonexistent-branch")

            assert result is False

    def test_reset_branch_to_origin_dry_run(self, mock_run_safe, capsys):
        """Test dry run doesn't execute reset."""
        with patch.object(operations, "run_git") as mock_run_git:
            result = operations.reset_branch_to_origin("feature/test", dry_run=True)

            mock_run_git.assert_not_called()
            assert result is True
            captured = capsys.readouterr()
            assert "[DRY RUN]" in captured.out

    def test_reset_branch_to_origin_exception_propagates(self, mock_run_safe):
        """Test exception during reset propagates to caller."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.side_effect = Exception("Git error")

            with pytest.raises(Exception, match="Git error"):
                operations.reset_branch_to_origin("feature/test")

    def test_reset_aborts_when_local_has_unpushed_commits(self, mock_run_safe, capsys):
        """Test reset aborts when local branch is ahead of origin."""
        with patch.object(operations, "run_git") as mock_run_git:
            # rev-list returns 3 commits ahead
            mock_run_git.return_value = MagicMock(returncode=0, stdout="3\n", stderr="")

            result = operations.reset_branch_to_origin("feature/test")

            assert result is False
            # Only the rev-list call should happen, no reset
            mock_run_git.assert_called_once()
            captured = capsys.readouterr()
            assert "unpushed commit" in captured.out
            assert "Aborting reset" in captured.out

    def test_reset_proceeds_when_rev_list_fails(self, mock_run_safe):
        """Test reset proceeds when rev-list check fails (e.g. no tracking branch)."""
        with patch.object(operations, "run_git") as mock_run_git:
            # rev-list fails (no tracking ref), reset succeeds
            mock_run_git.side_effect = [
                MagicMock(returncode=128, stdout="", stderr="unknown revision"),
                MagicMock(returncode=0, stdout="", stderr=""),
            ]

            result = operations.reset_branch_to_origin("feature/test")

            assert result is True
            assert mock_run_git.call_count == 2

    def test_reset_aborts_when_rev_list_output_unparseable(self, mock_run_safe, capsys):
        """Test reset aborts when rev-list output cannot be parsed as an integer."""
        with patch.object(operations, "run_git") as mock_run_git:
            # rev-list succeeds but returns non-numeric output
            mock_run_git.return_value = MagicMock(
                returncode=0, stdout="not-a-number\n", stderr=""
            )

            result = operations.reset_branch_to_origin("feature/test")

            assert result is False
            # Only the rev-list call should happen, no reset
            mock_run_git.assert_called_once()
            captured = capsys.readouterr()
            assert "Could not parse" in captured.out
            assert "safety precaution" in captured.out
