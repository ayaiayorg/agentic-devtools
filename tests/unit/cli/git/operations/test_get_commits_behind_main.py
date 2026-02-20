"""Tests for agentic_devtools.cli.git.operations.get_commits_behind_main."""

from unittest.mock import MagicMock

from agentic_devtools.cli.git import operations


class TestGetCommitsBehindMain:
    """Tests for get_commits_behind_main function."""

    def test_returns_count_when_behind(self, mock_run_safe):
        """Test returns correct count when behind main."""
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="5\n", stderr="")
        result = operations.get_commits_behind_main()
        assert result == 5

    def test_returns_zero_when_up_to_date(self, mock_run_safe):
        """Test returns 0 when up to date with main."""
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="0\n", stderr="")
        result = operations.get_commits_behind_main()
        assert result == 0

    def test_returns_zero_on_error(self, mock_run_safe):
        """Test returns 0 when git command fails."""
        mock_run_safe.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = operations.get_commits_behind_main()
        assert result == 0

    def test_returns_zero_on_invalid_count(self, mock_run_safe):
        """Test returns 0 when count is not a valid integer."""
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="invalid\n", stderr="")
        result = operations.get_commits_behind_main()
        assert result == 0
