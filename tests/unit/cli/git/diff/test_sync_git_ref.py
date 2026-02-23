"""Tests for agentic_devtools.cli.git.diff.sync_git_ref."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git.diff import sync_git_ref


class TestSyncGitRef:
    """Tests for sync_git_ref function."""

    def test_returns_false_for_empty_ref(self):
        """Should return False for empty ref."""
        assert sync_git_ref("") is False

    def test_returns_false_for_none_ref(self):
        """Should return False for None ref."""
        assert sync_git_ref(None) is False

    def test_returns_true_when_ref_exists_locally(self):
        """Should return True when ref exists locally."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_result):
            result = sync_git_ref("main")
            assert result is True

    def test_fetches_from_origin_when_not_local(self):
        """Should fetch from origin when ref doesn't exist locally."""
        mock_fail = MagicMock()
        mock_fail.returncode = 1
        mock_success = MagicMock()
        mock_success.returncode = 0

        with patch("agentic_devtools.cli.git.diff.run_safe", side_effect=[mock_fail, mock_success]) as mock_run:
            result = sync_git_ref("feature-branch")

            assert result is True
            assert mock_run.call_count == 2
            fetch_call = mock_run.call_args_list[1]
            assert "fetch" in fetch_call[0][0]

    def test_strips_origin_prefix_when_fetching(self):
        """Should strip origin/ prefix when fetching."""
        mock_fail = MagicMock()
        mock_fail.returncode = 1
        mock_success = MagicMock()
        mock_success.returncode = 0

        with patch("agentic_devtools.cli.git.diff.run_safe", side_effect=[mock_fail, mock_success]) as mock_run:
            result = sync_git_ref("origin/main")

            assert result is True
            fetch_call = mock_run.call_args_list[1]
            assert "main" in fetch_call[0][0]
            assert "origin/main" not in fetch_call[0][0]

    def test_returns_false_when_fetch_fails(self):
        """Should return False when both local check and fetch fail."""
        mock_fail = MagicMock()
        mock_fail.returncode = 1

        with patch("agentic_devtools.cli.git.diff.run_safe", return_value=mock_fail):
            result = sync_git_ref("nonexistent-branch")
            assert result is False
