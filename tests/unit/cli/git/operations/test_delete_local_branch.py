"""Tests for agentic_devtools.cli.git.operations.delete_local_branch."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.git import operations


class TestDeleteLocalBranch:
    """Tests for delete_local_branch function."""

    def test_delete_success(self, mock_run_safe):
        """Test successful branch deletion returns True."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = operations.delete_local_branch("my-branch")

            assert result is True
            mock_run_git.assert_called_once()
            call_args = mock_run_git.call_args[0]
            assert "branch" in call_args
            assert "-d" in call_args
            assert "my-branch" in call_args

    def test_delete_force(self, mock_run_safe):
        """Test force deletion uses -D flag."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = operations.delete_local_branch("my-branch", force=True)

            assert result is True
            call_args = mock_run_git.call_args[0]
            assert "-D" in call_args
            assert "-d" not in call_args

    def test_delete_failure_returns_false(self, mock_run_safe):
        """Test deletion failure returns False."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=1, stdout="", stderr="error: Cannot delete branch")

            result = operations.delete_local_branch("my-branch")

            assert result is False

    def test_delete_prints_success_message(self, mock_run_safe, capsys):
        """Test that a success message is printed after deletion."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

            operations.delete_local_branch("my-branch")

            captured = capsys.readouterr()
            assert "my-branch" in captured.out
            assert "Deleted" in captured.out

    def test_delete_prints_failure_message(self, mock_run_safe, capsys):
        """Test that a failure message is printed on deletion error."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=1, stdout="", stderr="fatal: Cannot delete branch")

            operations.delete_local_branch("my-branch")

            captured = capsys.readouterr()
            assert "Failed" in captured.out

    def test_delete_exception_propagates(self, mock_run_safe):
        """Test that an OSError during deletion propagates to the caller."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.side_effect = OSError("git not found")

            with pytest.raises(OSError, match="git not found"):
                operations.delete_local_branch("my-branch")
