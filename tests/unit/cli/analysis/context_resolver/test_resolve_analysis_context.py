"""Tests for resolve_analysis_context()."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agentic_devtools.cli.analysis.context_resolver import (
    resolve_analysis_context,
)


class TestResolveAnalysisContextIssueKey:
    """Happy path: --issue-key parameter."""

    def test_issue_key_resolves_worktree_key(self, tmp_path):
        with (
            patch(
                "agentic_devtools.cli.analysis.context_resolver._get_git_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "agentic_devtools.cli.analysis.context_resolver.get_state_dir",
                return_value=tmp_path / "state",
            ),
        ):
            ctx = resolve_analysis_context(issue_key="PROJECT-123")
            assert ctx.worktree_key == "PROJECT-123"
            assert ctx.source == "issue_key"
            assert ctx.git_root == tmp_path

    def test_issue_key_strips_whitespace(self, tmp_path):
        with (
            patch(
                "agentic_devtools.cli.analysis.context_resolver._get_git_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "agentic_devtools.cli.analysis.context_resolver.get_state_dir",
                return_value=tmp_path / "state",
            ),
        ):
            ctx = resolve_analysis_context(issue_key="  PROJECT-123  ")
            assert ctx.worktree_key == "PROJECT-123"


class TestResolveAnalysisContextPrId:
    """Happy path: --pr-id parameter."""

    def test_pr_id_resolves_worktree_key(self, tmp_path):
        with (
            patch(
                "agentic_devtools.cli.analysis.context_resolver._get_git_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "agentic_devtools.cli.analysis.context_resolver.get_state_dir",
                return_value=tmp_path / "state",
            ),
        ):
            ctx = resolve_analysis_context(pr_id=42)
            assert ctx.worktree_key == "PR42"
            assert ctx.source == "pr_id"


class TestResolveAnalysisContextBootstrapFallback:
    """Fallback to bootstrap worktree_key when neither param provided."""

    def test_bootstrap_fallback(self, tmp_path):
        with (
            patch(
                "agentic_devtools.cli.analysis.context_resolver.get_bootstrap_state",
                return_value={"worktree_key": "BOOT-KEY", "identity": "test"},
            ),
            patch(
                "agentic_devtools.cli.analysis.context_resolver._get_git_repo_root",
                return_value=tmp_path,
            ),
            patch(
                "agentic_devtools.cli.analysis.context_resolver.get_state_dir",
                return_value=tmp_path / "state",
            ),
        ):
            ctx = resolve_analysis_context()
            assert ctx.worktree_key == "BOOT-KEY"
            assert ctx.source == "bootstrap"

    def test_no_bootstrap_worktree_key_raises(self):
        with (
            patch(
                "agentic_devtools.cli.analysis.context_resolver.get_bootstrap_state",
                return_value={},
            ),
            pytest.raises(ValueError, match="No --issue-key or --pr-id"),
        ):
            resolve_analysis_context()


class TestResolveAnalysisContextErrors:
    """Error cases."""

    def test_mutual_exclusion(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            resolve_analysis_context(issue_key="X", pr_id=1)

    def test_empty_issue_key_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            resolve_analysis_context(issue_key="   ")

    def test_not_in_git_repo_raises(self):
        with (
            patch(
                "agentic_devtools.cli.analysis.context_resolver._get_git_repo_root",
                return_value=None,
            ),
        ):
            with pytest.raises(ValueError, match="Not in a git repository"):
                resolve_analysis_context(issue_key="KEY-1")

    def test_unsafe_issue_key_with_path_traversal_raises(self):
        """Issue key containing '../' is rejected as unsafe."""
        with pytest.raises(ValueError, match="not a safe directory segment"):
            resolve_analysis_context(issue_key="../escape")

    def test_unsafe_issue_key_with_slash_raises(self):
        """Issue key containing '/' is rejected as unsafe."""
        with pytest.raises(ValueError, match="not a safe directory segment"):
            resolve_analysis_context(issue_key="foo/bar")

    def test_unsafe_bootstrap_key_raises(self):
        """Bootstrap worktree_key with path traversal is rejected."""
        with (
            patch(
                "agentic_devtools.cli.analysis.context_resolver.get_bootstrap_state",
                return_value={"worktree_key": "../escape"},
            ),
            pytest.raises(ValueError, match="not a safe directory segment"),
        ):
            resolve_analysis_context()
