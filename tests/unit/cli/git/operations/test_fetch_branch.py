"""Tests for agentic_devtools.cli.git.operations.fetch_branch."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.git import operations


class TestFetchBranch:
    """Tests for fetch_branch function."""

    def test_fetch_branch_success(self, mock_run_safe):
        """Test successful branch fetch."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = operations.fetch_branch("feature/test")

            assert result is True
            mock_run_git.assert_called_once()
            call_args = mock_run_git.call_args[0]
            assert "fetch" in call_args
            assert "origin" in call_args

    def test_fetch_branch_failure(self, mock_run_safe):
        """Test branch fetch failure returns False."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=1, stdout="", stderr="error")

            result = operations.fetch_branch("nonexistent-branch")

            assert result is False

    def test_fetch_branch_dry_run(self, mock_run_safe, capsys):
        """Test dry run doesn't execute fetch."""
        with patch.object(operations, "run_git") as mock_run_git:
            result = operations.fetch_branch("feature/test", dry_run=True)

            mock_run_git.assert_not_called()
            assert result is True
            captured = capsys.readouterr()
            assert "[DRY RUN]" in captured.out

    def test_fetch_branch_exception_propagates(self, mock_run_safe):
        """Test exception during fetch propagates to caller."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.side_effect = Exception("Network error")

            with pytest.raises(Exception, match="Network error"):
                operations.fetch_branch("feature/test")
