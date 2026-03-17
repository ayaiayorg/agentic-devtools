"""Tests for agentic_devtools.cli.git.operations.get_short_commit_hash."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git import operations


class TestGetShortCommitHash:
    """Tests for get_short_commit_hash function."""

    def test_returns_hash_on_success(self, mock_run_safe):
        """Test returns the short hash string on success."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=0, stdout="abc1234\n", stderr="")

            result = operations.get_short_commit_hash("HEAD")

            assert result == "abc1234"
            mock_run_git.assert_called_once()
            call_args = mock_run_git.call_args[0]
            assert "rev-parse" in call_args
            assert "--short" in call_args
            assert "HEAD" in call_args

    def test_returns_none_on_failure(self, mock_run_safe):
        """Test returns None when git command fails."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=1, stdout="", stderr="fatal: not a valid object name")

            result = operations.get_short_commit_hash("nonexistent-ref")

            assert result is None

    def test_strips_whitespace_from_hash(self, mock_run_safe):
        """Test that leading/trailing whitespace is stripped from the hash."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=0, stdout="  deadbeef  \n", stderr="")

            result = operations.get_short_commit_hash("some-branch")

            assert result == "deadbeef"

    def test_returns_none_for_empty_output(self, mock_run_safe):
        """Test returns None when git returns an empty string."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = operations.get_short_commit_hash("HEAD")

            assert result is None
