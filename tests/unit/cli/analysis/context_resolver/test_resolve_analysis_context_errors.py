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
