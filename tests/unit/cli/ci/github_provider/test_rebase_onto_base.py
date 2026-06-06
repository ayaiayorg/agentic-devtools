"""Tests for GitHubActionsProvider.rebase_onto_base."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.pipeline.exceptions import (
    ForceWithLeaseError,
    RebaseConflictError,
)


class TestRebaseOntoBase:
    """Tests for rebase_onto_base method."""

    @patch.object(GitHubActionsProvider, "_run_git")
    def test_successful_rebase_and_push(self, mock_run_git) -> None:
        def git_side_effect(args):
            if args == ["rev-parse", "abc123"]:
                return "abc123\n"
            if args == ["rev-parse", "HEAD"]:
                return "abc123\n"
            return ""

        mock_run_git.side_effect = git_side_effect
        provider = GitHubActionsProvider(repo="owner/repo")

        provider.rebase_onto_base(pr_number=1, base_branch="main", head_branch="feature", head_sha="abc123")

        mock_run_git.assert_any_call(["fetch", "origin", "main", "feature"])
        mock_run_git.assert_any_call(["checkout", "feature"])
        mock_run_git.assert_any_call(["rebase", "origin/main"])
        mock_run_git.assert_any_call(["push", "--force-with-lease", "origin", "HEAD:feature"])

    @patch.object(GitHubActionsProvider, "_resolve_rebase_conflicts_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_raises_rebase_conflict_error_when_unresolvable(self, mock_run_git, mock_resolve) -> None:
        def git_side_effect(args):
            if args == ["rev-parse", "abc123"]:
                return "abc123\n"
            if args == ["rev-parse", "HEAD"]:
                return "abc123\n"
            if args == ["rebase", "origin/main"]:
                raise RuntimeError("conflict")
            if args == ["rebase", "--abort"]:
                return ""
            return ""

        mock_run_git.side_effect = git_side_effect
        mock_resolve.return_value = False
        provider = GitHubActionsProvider(repo="owner/repo")

        with pytest.raises(RebaseConflictError, match="could not be auto-resolved"):
            provider.rebase_onto_base(pr_number=1, base_branch="main", head_branch="feature", head_sha="abc123")

    @patch.object(GitHubActionsProvider, "_resolve_rebase_conflicts_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_raises_rebase_conflict_error_when_abort_fails(self, mock_run_git, mock_resolve) -> None:
        def git_side_effect(args):
            if args == ["rev-parse", "abc123"]:
                return "abc123\n"
            if args == ["rev-parse", "HEAD"]:
                return "abc123\n"
            if args == ["rebase", "origin/main"]:
                raise RuntimeError("conflict")
            if args == ["rebase", "--abort"]:
                raise RuntimeError("abort failed")
            return ""

        mock_run_git.side_effect = git_side_effect
        mock_resolve.return_value = False
        provider = GitHubActionsProvider(repo="owner/repo")

        with pytest.raises(RebaseConflictError, match="abort failed"):
            provider.rebase_onto_base(pr_number=1, base_branch="main", head_branch="feature", head_sha="abc123")

    @patch.object(GitHubActionsProvider, "_run_git")
    def test_raises_force_with_lease_error_on_push_failure(self, mock_run_git) -> None:
        def git_side_effect(args):
            if args == ["rev-parse", "abc123"]:
                return "abc123\n"
            if args == ["rev-parse", "HEAD"]:
                return "abc123\n"
            if args == ["push", "--force-with-lease", "origin", "HEAD:feature"]:
                raise RuntimeError("push rejected")
            return ""

        mock_run_git.side_effect = git_side_effect
        provider = GitHubActionsProvider(repo="owner/repo")

        with pytest.raises(ForceWithLeaseError, match="push rejected"):
            provider.rebase_onto_base(pr_number=1, base_branch="main", head_branch="feature", head_sha="abc123")

    @patch.object(GitHubActionsProvider, "_resolve_rebase_conflicts_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_successful_rebase_after_conflict_resolution(self, mock_run_git, mock_resolve) -> None:
        call_count = {"rebase": 0}

        def git_side_effect(args):
            if args == ["rev-parse", "abc123"]:
                return "abc123\n"
            if args == ["rev-parse", "HEAD"]:
                return "abc123\n"
            if args == ["rebase", "origin/main"]:
                call_count["rebase"] += 1
                if call_count["rebase"] == 1:
                    raise RuntimeError("conflict")
            return ""

        mock_run_git.side_effect = git_side_effect
        mock_resolve.return_value = True
        provider = GitHubActionsProvider(repo="owner/repo")

        provider.rebase_onto_base(pr_number=1, base_branch="main", head_branch="feature", head_sha="abc123")

        mock_run_git.assert_any_call(["push", "--force-with-lease", "origin", "HEAD:feature"])

    @patch.object(GitHubActionsProvider, "_resolve_rebase_conflicts_via_sdk")
    @patch.object(GitHubActionsProvider, "_run_git")
    def test_raises_rebase_conflict_when_resolve_raises(self, mock_run_git, mock_resolve) -> None:
        def git_side_effect(args):
            if args == ["rev-parse", "abc123"]:
                return "abc123\n"
            if args == ["rev-parse", "HEAD"]:
                return "abc123\n"
            if args == ["rebase", "origin/main"]:
                raise RuntimeError("conflict")
            if args == ["rebase", "--abort"]:
                return ""
            return ""

        mock_run_git.side_effect = git_side_effect
        mock_resolve.side_effect = RuntimeError("SDK failure")
        provider = GitHubActionsProvider(repo="owner/repo")

        with pytest.raises(RebaseConflictError, match="could not be auto-resolved"):
            provider.rebase_onto_base(pr_number=1, base_branch="main", head_branch="feature", head_sha="abc123")

    @patch.object(GitHubActionsProvider, "_run_git")
    def test_raises_when_checked_out_head_differs_from_snapshot(self, mock_run_git) -> None:
        def git_side_effect(args):
            if args == ["rev-parse", "abc123"]:
                return "abc123\n"
            if args == ["rev-parse", "HEAD"]:
                return "def456\n"
            return ""

        mock_run_git.side_effect = git_side_effect
        provider = GitHubActionsProvider(repo="owner/repo")

        with pytest.raises(RuntimeError, match="Head SHA changed before rebase"):
            provider.rebase_onto_base(pr_number=1, base_branch="main", head_branch="feature", head_sha="abc123")
