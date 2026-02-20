"""Tests for agentic_devtools.cli.git.operations.last_commit_contains_issue_key."""

from unittest.mock import MagicMock

from agentic_devtools.cli.git import operations


class TestLastCommitContainsIssueKey:
    """Tests for last_commit_contains_issue_key function."""

    def test_returns_true_when_key_found(self, mock_run_safe):
        """Test returns True when issue key is in commit message."""
        mock_run_safe.return_value = MagicMock(
            returncode=0, stdout="feature(DFLY-1234): implement feature\n", stderr=""
        )

        result = operations.last_commit_contains_issue_key("DFLY-1234")

        assert result is True

    def test_returns_true_case_insensitive(self, mock_run_safe):
        """Test matching is case-insensitive."""
        mock_run_safe.return_value = MagicMock(
            returncode=0, stdout="feature(dfly-1234): implement feature\n", stderr=""
        )

        result = operations.last_commit_contains_issue_key("DFLY-1234")

        assert result is True

    def test_returns_false_when_key_not_found(self, mock_run_safe):
        """Test returns False when issue key is not in commit message."""
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="feature(DFLY-5678): different issue\n", stderr="")

        result = operations.last_commit_contains_issue_key("DFLY-1234")

        assert result is False

    def test_returns_false_on_error(self, mock_run_safe):
        """Test returns False on git command error."""
        mock_run_safe.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        result = operations.last_commit_contains_issue_key("DFLY-1234")

        assert result is False
