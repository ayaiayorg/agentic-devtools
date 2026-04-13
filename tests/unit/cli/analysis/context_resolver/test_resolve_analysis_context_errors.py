"""Error clarity tests for resolve_analysis_context() — NFR-004."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agentic_devtools.cli.analysis.context_resolver import resolve_analysis_context


class TestResolveAnalysisContextErrors:
    """NFR-004: Error messages include the specific parameter or path."""

    def test_mutual_exclusion_error_message(self):
        """EC1: Both params → exact error string."""
        with pytest.raises(ValueError, match="--issue-key and --pr-id are mutually exclusive"):
            resolve_analysis_context(issue_key="X", pr_id=1)

    def test_empty_issue_key_error_message(self):
        """EC2: Empty --issue-key → usage error."""
        with pytest.raises(ValueError, match="--issue-key value must not be empty"):
            resolve_analysis_context(issue_key="")

    def test_missing_bootstrap_error_message(self):
        """Missing bootstrap worktree key → descriptive error."""
        with (
            patch(
                "agentic_devtools.cli.analysis.context_resolver._get_git_repo_root",
                return_value="/fake/repo",
            ),
            patch(
                "agentic_devtools.cli.analysis.context_resolver.get_bootstrap_state",
                return_value={},
            ),
            pytest.raises(ValueError, match="No --issue-key or --pr-id"),
        ):
            resolve_analysis_context()

    def test_not_in_git_repo_error_message(self):
        """Not in a git repo → error includes 'git repository'."""
        with (
            patch(
                "agentic_devtools.cli.analysis.context_resolver._get_git_repo_root",
                return_value=None,
            ),
            pytest.raises(ValueError, match="Not in a git repository"),
        ):
            resolve_analysis_context(issue_key="KEY-1")

    def test_pr_id_non_int_raises_value_error(self):
        """--pr-id with a non-int type → usage error."""
        with pytest.raises(ValueError, match="--pr-id must be an integer"):
            resolve_analysis_context(pr_id=1.5)  # type: ignore[arg-type]

    def test_pr_id_string_raises_value_error(self):
        """--pr-id with a string → usage error."""
        with pytest.raises(ValueError, match="--pr-id must be an integer"):
            resolve_analysis_context(pr_id="abc")  # type: ignore[arg-type]

    def test_pr_id_bool_raises_value_error(self):
        """--pr-id with a bool → usage error (bool is subclass of int)."""
        with pytest.raises(ValueError, match="--pr-id must be an integer"):
            resolve_analysis_context(pr_id=True)  # type: ignore[arg-type]

    def test_pr_id_zero_raises_value_error(self):
        """--pr-id of 0 → usage error."""
        with pytest.raises(ValueError, match="--pr-id must be a positive integer"):
            resolve_analysis_context(pr_id=0)

    def test_pr_id_negative_raises_value_error(self):
        """--pr-id of negative number → usage error."""
        with pytest.raises(ValueError, match="--pr-id must be a positive integer"):
            resolve_analysis_context(pr_id=-5)

    def test_bootstrap_not_in_git_repo_gives_accurate_error(self):
        """When not in a git repo and no params, error should say 'git repository'."""
        with (
            patch(
                "agentic_devtools.cli.analysis.context_resolver._get_git_repo_root",
                return_value=None,
            ),
            pytest.raises(ValueError, match="Not in a git repository"),
        ):
            resolve_analysis_context()
