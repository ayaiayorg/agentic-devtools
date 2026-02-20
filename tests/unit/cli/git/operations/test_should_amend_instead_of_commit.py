"""Tests for agentic_devtools.cli.git.operations.should_amend_instead_of_commit."""

from unittest.mock import patch

from agentic_devtools.cli.git import operations


class TestShouldAmendInsteadOfCommit:
    """Tests for should_amend_instead_of_commit function."""

    def test_returns_false_when_no_commits_ahead(self, mock_run_safe):
        """Test returns False when branch has no commits ahead of main."""
        with patch.object(operations, "branch_has_commits_ahead_of_main", return_value=False):
            result = operations.should_amend_instead_of_commit("DFLY-1234")
            assert result is False

    def test_returns_true_when_commits_ahead_with_issue_key(self, mock_run_safe):
        """Test returns True when commits ahead, regardless of issue key match."""
        with patch.object(operations, "branch_has_commits_ahead_of_main", return_value=True):
            result = operations.should_amend_instead_of_commit("DFLY-1234")
            assert result is True

    def test_returns_true_when_commits_ahead_with_different_issue_key(self, mock_run_safe):
        """Test returns True even when issue key doesn't match last commit."""
        with patch.object(operations, "branch_has_commits_ahead_of_main", return_value=True):
            result = operations.should_amend_instead_of_commit("DIFFERENT-KEY")
            assert result is True

    def test_returns_true_when_no_issue_key_and_commits_ahead(self, mock_run_safe):
        """Test returns True when no issue key provided but commits ahead."""
        with patch.object(operations, "branch_has_commits_ahead_of_main", return_value=True):
            result = operations.should_amend_instead_of_commit(None)
            assert result is True
