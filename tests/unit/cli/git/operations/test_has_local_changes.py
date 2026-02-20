"""Tests for agentic_devtools.cli.git.operations.has_local_changes."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git import operations


class TestHasLocalChanges:
    """Tests for has_local_changes function."""

    def test_staged_changes_returns_true(self, mock_run_safe):
        """When there are staged changes, should return True."""
        mock_result_staged = MagicMock()
        mock_result_staged.returncode = 1  # Non-zero = has staged changes

        with patch.object(operations, "run_git", return_value=mock_result_staged):
            result = operations.has_local_changes()

        assert result is True

    def test_unstaged_changes_returns_true(self, mock_run_safe):
        """When there are unstaged changes, should return True."""
        mock_result_no_staged = MagicMock()
        mock_result_no_staged.returncode = 0

        mock_result_unstaged = MagicMock()
        mock_result_unstaged.returncode = 1  # Non-zero = has unstaged changes

        with patch.object(
            operations,
            "run_git",
            side_effect=[mock_result_no_staged, mock_result_unstaged],
        ):
            result = operations.has_local_changes()

        assert result is True

    def test_untracked_files_returns_true(self, mock_run_safe):
        """When there are untracked files, should return True."""
        mock_result_clean = MagicMock()
        mock_result_clean.returncode = 0

        mock_result_untracked = MagicMock()
        mock_result_untracked.returncode = 0
        mock_result_untracked.stdout = "new_file.txt\nanother_file.py\n"

        with patch.object(
            operations,
            "run_git",
            side_effect=[mock_result_clean, mock_result_clean, mock_result_untracked],
        ):
            result = operations.has_local_changes()

        assert result is True

    def test_clean_working_directory_returns_false(self, mock_run_safe):
        """When working directory is clean, should return False."""
        mock_result_clean = MagicMock()
        mock_result_clean.returncode = 0

        mock_result_no_untracked = MagicMock()
        mock_result_no_untracked.returncode = 0
        mock_result_no_untracked.stdout = ""

        with patch.object(
            operations,
            "run_git",
            side_effect=[mock_result_clean, mock_result_clean, mock_result_no_untracked],
        ):
            result = operations.has_local_changes()

        assert result is False

    def test_untracked_with_only_whitespace_returns_false(self, mock_run_safe):
        """When untracked output is only whitespace, should return False."""
        mock_result_clean = MagicMock()
        mock_result_clean.returncode = 0

        mock_result_whitespace = MagicMock()
        mock_result_whitespace.returncode = 0
        mock_result_whitespace.stdout = "   \n  \n"

        with patch.object(
            operations,
            "run_git",
            side_effect=[mock_result_clean, mock_result_clean, mock_result_whitespace],
        ):
            result = operations.has_local_changes()

        assert result is False
