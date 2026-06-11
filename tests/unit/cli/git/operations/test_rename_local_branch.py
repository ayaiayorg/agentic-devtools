"""Tests for agentic_devtools.cli.git.operations.rename_local_branch."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.git import operations


class TestRenameLocalBranch:
    """Tests for rename_local_branch function."""

    def test_rename_success(self, mock_run_safe):
        """Test successful branch rename returns True."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = operations.rename_local_branch("old-branch", "new-branch")

            assert result is True
            mock_run_git.assert_called_once()
            call_args = mock_run_git.call_args[0]
            assert "branch" in call_args
            assert "-m" in call_args
            assert "old-branch" in call_args
            assert "new-branch" in call_args

    def test_rename_failure_returns_false(self, mock_run_safe):
        """Test rename failure returns False."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=1, stdout="", stderr="error: branch already exists")

            result = operations.rename_local_branch("old-branch", "existing-branch")

            assert result is False

    def test_rename_failure_no_stderr(self, mock_run_safe, capsys):
        """Test rename failure with empty stderr."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=1, stdout="", stderr="")

            result = operations.rename_local_branch("old-branch", "new-branch")

            assert result is False
            captured = capsys.readouterr()
            assert "Failed to rename" in captured.out

    def test_rename_prints_success_message(self, mock_run_safe, capsys):
        """Test that a success message is printed on rename."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

            operations.rename_local_branch("old-branch", "new-branch")

            captured = capsys.readouterr()
            assert "old-branch" in captured.out
            assert "new-branch" in captured.out

    def test_rename_prints_failure_message(self, mock_run_safe, capsys):
        """Test that a failure message is printed on rename error."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=1, stdout="", stderr="fatal: branch already exists")

            operations.rename_local_branch("old-branch", "new-branch")

            captured = capsys.readouterr()
            assert "Failed" in captured.out

    def test_rename_exception_propagates(self, mock_run_safe):
        """Test that an OSError during rename propagates to the caller."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.side_effect = OSError("git not found")

            with pytest.raises(OSError, match="git not found"):
                operations.rename_local_branch("old-branch", "new-branch")
