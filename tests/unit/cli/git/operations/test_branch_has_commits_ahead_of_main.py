"""Tests for agentic_devtools.cli.git.operations.branch_has_commits_ahead_of_main."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git import operations


class TestBranchHasCommitsAheadOfMain:
    """Tests for branch_has_commits_ahead_of_main function."""

    def test_returns_true_when_ahead(self, mock_run_safe):
        """Test returns True when branch is ahead of main."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # rev-parse origin/main
                MagicMock(returncode=0, stdout="3\n", stderr=""),  # 3 commits ahead
            ]
            result = operations.branch_has_commits_ahead_of_main()
            assert result is True

    def test_returns_false_when_not_ahead(self, mock_run_safe):
        """Test returns False when branch is not ahead."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # rev-parse origin/main
                MagicMock(returncode=0, stdout="0\n", stderr=""),  # 0 commits ahead
            ]
            result = operations.branch_has_commits_ahead_of_main()
            assert result is False

    def test_returns_false_when_on_main(self, mock_run_safe):
        """Test returns False when already on main branch."""
        with patch.object(operations, "get_current_branch", return_value="main"):
            result = operations.branch_has_commits_ahead_of_main()
            assert result is False

    def test_fallback_to_main_without_origin(self, mock_run_safe):
        """Test falls back to main when origin/main doesn't exist."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=1, stdout="", stderr="not found"),  # origin/main fails
                MagicMock(returncode=0, stdout="", stderr=""),  # main succeeds
                MagicMock(returncode=0, stdout="2\n", stderr=""),  # 2 commits ahead
            ]
            result = operations.branch_has_commits_ahead_of_main()
            assert result is True

    def test_returns_false_when_main_not_found(self, mock_run_safe):
        """Test returns False when neither origin/main nor main exists."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=1, stdout="", stderr="not found"),  # origin/main fails
                MagicMock(returncode=1, stdout="", stderr="not found"),  # main also fails
            ]
            result = operations.branch_has_commits_ahead_of_main()
            assert result is False

    def test_returns_false_on_rev_list_error(self, mock_run_safe):
        """Test returns False when rev-list fails."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # rev-parse succeeds
                MagicMock(returncode=1, stdout="", stderr="error"),  # rev-list fails
            ]
            result = operations.branch_has_commits_ahead_of_main()
            assert result is False

    def test_returns_false_on_invalid_count(self, mock_run_safe):
        """Test returns False when count is not a valid integer."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # rev-parse succeeds
                MagicMock(returncode=0, stdout="invalid\n", stderr=""),  # invalid count
            ]
            result = operations.branch_has_commits_ahead_of_main()
            assert result is False
