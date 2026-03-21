"""Tests for CheckWorktreeAndBranch."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.workflows.preflight import (
    check_worktree_and_branch,
)


class TestCheckWorktreeAndBranch:
    """Tests for check_worktree_and_branch function."""

    def test_both_valid_case_insensitive(self):
        """Test that checking is case-insensitive."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch(
            "agentic_devtools.cli.workflows.preflight.get_current_git_branch"
        ) as mock_branch, patch("agentic_devtools.cli.workflows.preflight.get_git_repo_root") as mock_root:
            mock_cwd.return_value = Path("/repos/dfly-1850")
            mock_branch.return_value = "feature/DFLY-1850/test"
            mock_root.return_value = "/repos/dfly-1850"

            result = check_worktree_and_branch("DFLY-1850")

            assert result.folder_valid is True
            assert result.branch_valid is True
            assert result.passed is True

    def test_folder_contains_key(self):
        """Test that folder containing the key passes."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch(
            "agentic_devtools.cli.workflows.preflight.get_current_git_branch"
        ) as mock_branch, patch("agentic_devtools.cli.workflows.preflight.get_git_repo_root") as mock_root:
            mock_cwd.return_value = Path("/repos/my-DFLY-1850-work")
            mock_branch.return_value = "feature/DFLY-1850/work"
            mock_root.return_value = "/repos/my-DFLY-1850-work"

            result = check_worktree_and_branch("DFLY-1850")

            assert result.folder_valid is True

    def test_branch_missing(self):
        """Test when no branch is checked out."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch(
            "agentic_devtools.cli.workflows.preflight.get_current_git_branch"
        ) as mock_branch, patch("agentic_devtools.cli.workflows.preflight.get_git_repo_root") as mock_root:
            mock_cwd.return_value = Path("/repos/DFLY-1850")
            mock_branch.return_value = None
            mock_root.return_value = None

            result = check_worktree_and_branch("DFLY-1850")

            assert result.branch_valid is False

    def test_source_branch_match_for_pr_review_without_jira(self):
        """Test that branch validation passes when source_branch matches current branch.

        This is critical for PR review workflows without a Jira issue key, where
        the folder is PR{id} but the branch is the actual PR source branch.
        """
        with patch("pathlib.Path.cwd") as mock_cwd, patch(
            "agentic_devtools.cli.workflows.preflight.get_current_git_branch"
        ) as mock_branch, patch("agentic_devtools.cli.workflows.preflight.get_git_repo_root") as mock_root:
            mock_cwd.return_value = Path("/repos/PR24031")
            mock_branch.return_value = "feature/dfly-test-file-source-file-param"
            mock_root.return_value = "/repos/PR24031"

            # issue_key is PR24031 (folder matches) but branch doesn't contain PR24031
            # However, source_branch matches so it should pass
            result = check_worktree_and_branch(
                "PR24031",
                source_branch="feature/dfly-test-file-source-file-param",
            )

            assert result.folder_valid is True
            assert result.branch_valid is True
            assert result.matched_by_source_branch is True
            assert result.passed is True

    def test_source_branch_match_with_refs_heads_prefix(self):
        """Test that source_branch normalization handles refs/heads/ prefix."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch(
            "agentic_devtools.cli.workflows.preflight.get_current_git_branch"
        ) as mock_branch, patch("agentic_devtools.cli.workflows.preflight.get_git_repo_root") as mock_root:
            mock_cwd.return_value = Path("/repos/PR12345")
            mock_branch.return_value = "feature/my-branch"
            mock_root.return_value = "/repos/PR12345"

            # source_branch has refs/heads/ prefix from Azure DevOps API
            result = check_worktree_and_branch(
                "PR12345",
                source_branch="refs/heads/feature/my-branch",
            )

            assert result.branch_valid is True
            assert result.matched_by_source_branch is True

    def test_source_branch_no_match_when_different(self):
        """Test that source_branch doesn't match when branches are different."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch(
            "agentic_devtools.cli.workflows.preflight.get_current_git_branch"
        ) as mock_branch, patch("agentic_devtools.cli.workflows.preflight.get_git_repo_root") as mock_root:
            mock_cwd.return_value = Path("/repos/PR24031")
            mock_branch.return_value = "main"
            mock_root.return_value = "/repos/PR24031"

            result = check_worktree_and_branch(
                "PR24031",
                source_branch="feature/different-branch",
            )

            assert result.folder_valid is True
            assert result.branch_valid is False  # Branch doesn't match
            assert result.matched_by_source_branch is False

    def test_issue_key_match_preferred_over_source_branch(self):
        """Test that issue_key in branch is used when available, not source_branch match."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch(
            "agentic_devtools.cli.workflows.preflight.get_current_git_branch"
        ) as mock_branch, patch("agentic_devtools.cli.workflows.preflight.get_git_repo_root") as mock_root:
            mock_cwd.return_value = Path("/repos/DFLY-1850")
            mock_branch.return_value = "feature/DFLY-1850/my-work"
            mock_root.return_value = "/repos/DFLY-1850"

            result = check_worktree_and_branch(
                "DFLY-1850",
                source_branch="feature/some-other-branch",
            )

            # Branch contains issue key so matched_by_source_branch should be False
            assert result.branch_valid is True
            assert result.matched_by_source_branch is False
