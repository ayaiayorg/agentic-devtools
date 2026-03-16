"""Tests for agentic_devtools.cli.git.operations.reset_branch_to_origin."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.git import operations


class TestResetBranchToOrigin:
    """Tests for reset_branch_to_origin function."""

    def test_reset_branch_to_origin_success(self, mock_run_safe):
        """Test successful branch reset."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = operations.reset_branch_to_origin("feature/test")

            assert result is True
            mock_run_git.assert_called_once()
            call_args = mock_run_git.call_args[0]
            assert "reset" in call_args
            assert "--hard" in call_args
            assert "origin/feature/test" in call_args

    def test_reset_branch_to_origin_failure(self, mock_run_safe):
        """Test branch reset failure returns False."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=1, stdout="", stderr="error")

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
