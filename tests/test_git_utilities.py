"""Tests for git utility functions: has_local_changes and local_branch_matches_origin."""

from unittest.mock import MagicMock, patch

from dfly_ai_helpers.cli.git import operations


class TestHasLocalChanges:
    """Tests for has_local_changes function."""

    def test_staged_changes_returns_true(self):
        """When there are staged changes, should return True."""
        # diff --cached returns non-zero when there are staged changes
        mock_result_staged = MagicMock()
        mock_result_staged.returncode = 1  # Non-zero = has staged changes

        with patch.object(operations, "run_git", return_value=mock_result_staged):
            result = operations.has_local_changes()

        assert result is True

    def test_unstaged_changes_returns_true(self):
        """When there are unstaged changes, should return True."""
        # Staged check passes (no staged), unstaged check fails
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

    def test_untracked_files_returns_true(self):
        """When there are untracked files, should return True."""
        # Staged check passes, unstaged check passes, untracked check finds files
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

    def test_clean_working_directory_returns_false(self):
        """When working directory is clean, should return False."""
        mock_result_clean = MagicMock()
        mock_result_clean.returncode = 0

        mock_result_no_untracked = MagicMock()
        mock_result_no_untracked.returncode = 0
        mock_result_no_untracked.stdout = ""  # Empty = no untracked files

        with patch.object(
            operations,
            "run_git",
            side_effect=[mock_result_clean, mock_result_clean, mock_result_no_untracked],
        ):
            result = operations.has_local_changes()

        assert result is False

    def test_untracked_with_only_whitespace_returns_false(self):
        """When untracked output is only whitespace, should return False."""
        mock_result_clean = MagicMock()
        mock_result_clean.returncode = 0

        mock_result_whitespace = MagicMock()
        mock_result_whitespace.returncode = 0
        mock_result_whitespace.stdout = "   \n  \n"  # Only whitespace

        with patch.object(
            operations,
            "run_git",
            side_effect=[mock_result_clean, mock_result_clean, mock_result_whitespace],
        ):
            result = operations.has_local_changes()

        assert result is False


class TestLocalBranchMatchesOrigin:
    """Tests for local_branch_matches_origin function."""

    def test_in_sync_returns_true(self):
        """When local and origin are in sync, should return True."""
        mock_origin_exists = MagicMock()
        mock_origin_exists.returncode = 0

        mock_ahead = MagicMock()
        mock_ahead.returncode = 0
        mock_ahead.stdout = "0\n"  # 0 commits ahead

        mock_behind = MagicMock()
        mock_behind.returncode = 0
        mock_behind.stdout = "0\n"  # 0 commits behind

        with patch.object(
            operations,
            "get_current_branch",
            return_value="feature/test-branch",
        ), patch.object(
            operations,
            "run_git",
            side_effect=[mock_origin_exists, mock_ahead, mock_behind],
        ):
            result = operations.local_branch_matches_origin()

        assert result is True

    def test_ahead_of_origin_returns_false(self):
        """When local is ahead of origin, should return False."""
        mock_origin_exists = MagicMock()
        mock_origin_exists.returncode = 0

        mock_ahead = MagicMock()
        mock_ahead.returncode = 0
        mock_ahead.stdout = "3\n"  # 3 commits ahead

        mock_behind = MagicMock()
        mock_behind.returncode = 0
        mock_behind.stdout = "0\n"

        with patch.object(
            operations,
            "get_current_branch",
            return_value="feature/test-branch",
        ), patch.object(
            operations,
            "run_git",
            side_effect=[mock_origin_exists, mock_ahead, mock_behind],
        ):
            result = operations.local_branch_matches_origin()

        assert result is False

    def test_behind_origin_returns_false(self):
        """When local is behind origin, should return False."""
        mock_origin_exists = MagicMock()
        mock_origin_exists.returncode = 0

        mock_ahead = MagicMock()
        mock_ahead.returncode = 0
        mock_ahead.stdout = "0\n"

        mock_behind = MagicMock()
        mock_behind.returncode = 0
        mock_behind.stdout = "2\n"  # 2 commits behind

        with patch.object(
            operations,
            "get_current_branch",
            return_value="feature/test-branch",
        ), patch.object(
            operations,
            "run_git",
            side_effect=[mock_origin_exists, mock_ahead, mock_behind],
        ):
            result = operations.local_branch_matches_origin()

        assert result is False

    def test_origin_branch_not_exists_returns_false(self):
        """When origin branch doesn't exist, should return False."""
        mock_origin_not_exists = MagicMock()
        mock_origin_not_exists.returncode = 128  # Git error - ref not found

        with patch.object(
            operations,
            "get_current_branch",
            return_value="feature/new-branch",
        ), patch.object(
            operations,
            "run_git",
            return_value=mock_origin_not_exists,
        ):
            result = operations.local_branch_matches_origin()

        assert result is False

    def test_ahead_count_parse_error_returns_false(self):
        """When ahead count can't be parsed, should return False."""
        mock_origin_exists = MagicMock()
        mock_origin_exists.returncode = 0

        mock_ahead_bad = MagicMock()
        mock_ahead_bad.returncode = 0
        mock_ahead_bad.stdout = "not-a-number\n"  # Invalid output

        with patch.object(
            operations,
            "get_current_branch",
            return_value="feature/test-branch",
        ), patch.object(
            operations,
            "run_git",
            side_effect=[mock_origin_exists, mock_ahead_bad],
        ):
            result = operations.local_branch_matches_origin()

        assert result is False

    def test_behind_count_parse_error_returns_false(self):
        """When behind count can't be parsed, should return False."""
        mock_origin_exists = MagicMock()
        mock_origin_exists.returncode = 0

        mock_ahead = MagicMock()
        mock_ahead.returncode = 0
        mock_ahead.stdout = "0\n"

        mock_behind_bad = MagicMock()
        mock_behind_bad.returncode = 0
        mock_behind_bad.stdout = "invalid\n"  # Invalid output

        with patch.object(
            operations,
            "get_current_branch",
            return_value="feature/test-branch",
        ), patch.object(
            operations,
            "run_git",
            side_effect=[mock_origin_exists, mock_ahead, mock_behind_bad],
        ):
            result = operations.local_branch_matches_origin()

        assert result is False

    def test_ahead_command_fails_returns_false(self):
        """When rev-list for ahead fails, should return False."""
        mock_origin_exists = MagicMock()
        mock_origin_exists.returncode = 0

        mock_ahead_fail = MagicMock()
        mock_ahead_fail.returncode = 1  # Command failed

        with patch.object(
            operations,
            "get_current_branch",
            return_value="feature/test-branch",
        ), patch.object(
            operations,
            "run_git",
            side_effect=[mock_origin_exists, mock_ahead_fail],
        ):
            result = operations.local_branch_matches_origin()

        assert result is False

    def test_behind_command_fails_returns_false(self):
        """When rev-list for behind fails, should return False."""
        mock_origin_exists = MagicMock()
        mock_origin_exists.returncode = 0

        mock_ahead = MagicMock()
        mock_ahead.returncode = 0
        mock_ahead.stdout = "0\n"

        mock_behind_fail = MagicMock()
        mock_behind_fail.returncode = 1  # Command failed

        with patch.object(
            operations,
            "get_current_branch",
            return_value="feature/test-branch",
        ), patch.object(
            operations,
            "run_git",
            side_effect=[mock_origin_exists, mock_ahead, mock_behind_fail],
        ):
            result = operations.local_branch_matches_origin()

        assert result is False
