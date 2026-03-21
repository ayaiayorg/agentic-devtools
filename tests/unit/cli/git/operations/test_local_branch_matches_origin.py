"""Tests for agentic_devtools.cli.git.operations.local_branch_matches_origin."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git import operations


class TestLocalBranchMatchesOrigin:
    """Tests for local_branch_matches_origin function."""

    def test_in_sync_returns_true(self, mock_run_safe):
        """When local and origin are in sync, should return True."""
        mock_origin_exists = MagicMock()
        mock_origin_exists.returncode = 0

        mock_ahead = MagicMock()
        mock_ahead.returncode = 0
        mock_ahead.stdout = "0\n"

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

        assert result is True

    def test_ahead_of_origin_returns_false(self, mock_run_safe):
        """When local is ahead of origin, should return False."""
        mock_origin_exists = MagicMock()
        mock_origin_exists.returncode = 0

        mock_ahead = MagicMock()
        mock_ahead.returncode = 0
        mock_ahead.stdout = "3\n"

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

    def test_behind_origin_returns_false(self, mock_run_safe):
        """When local is behind origin, should return False."""
        mock_origin_exists = MagicMock()
        mock_origin_exists.returncode = 0

        mock_ahead = MagicMock()
        mock_ahead.returncode = 0
        mock_ahead.stdout = "0\n"

        mock_behind = MagicMock()
        mock_behind.returncode = 0
        mock_behind.stdout = "2\n"

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

    def test_origin_branch_not_exists_returns_false(self, mock_run_safe):
        """When origin branch doesn't exist, should return False."""
        mock_origin_not_exists = MagicMock()
        mock_origin_not_exists.returncode = 128

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

    def test_ahead_count_parse_error_returns_false(self, mock_run_safe):
        """When ahead count can't be parsed, should return False."""
        mock_origin_exists = MagicMock()
        mock_origin_exists.returncode = 0

        mock_ahead_bad = MagicMock()
        mock_ahead_bad.returncode = 0
        mock_ahead_bad.stdout = "not-a-number\n"

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

    def test_behind_count_parse_error_returns_false(self, mock_run_safe):
        """When behind count can't be parsed, should return False."""
        mock_origin_exists = MagicMock()
        mock_origin_exists.returncode = 0

        mock_ahead = MagicMock()
        mock_ahead.returncode = 0
        mock_ahead.stdout = "0\n"

        mock_behind_bad = MagicMock()
        mock_behind_bad.returncode = 0
        mock_behind_bad.stdout = "invalid\n"

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

    def test_ahead_command_fails_returns_false(self, mock_run_safe):
        """When rev-list for ahead fails, should return False."""
        mock_origin_exists = MagicMock()
        mock_origin_exists.returncode = 0

        mock_ahead_fail = MagicMock()
        mock_ahead_fail.returncode = 1

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

    def test_behind_command_fails_returns_false(self, mock_run_safe):
        """When rev-list for behind fails, should return False."""
        mock_origin_exists = MagicMock()
        mock_origin_exists.returncode = 0

        mock_ahead = MagicMock()
        mock_ahead.returncode = 0
        mock_ahead.stdout = "0\n"

        mock_behind_fail = MagicMock()
        mock_behind_fail.returncode = 1

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
