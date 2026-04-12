"""Edge case tests for resolve_analysis_context() and related functions."""

from __future__ import annotations

import pytest

from agentic_devtools.cli.analysis.context_resolver import (
    list_worktree_state_dirs,
    resolve_analysis_context,
)
from agentic_devtools.cli.analysis.external_context import collect_external_context
from agentic_devtools.cli.analysis.identity_scanner import scan_identity_logs


class TestResolveAnalysisContextEdgeCases:
    """Edge cases from spec EC1–EC7."""

    def test_ec1_mutual_exclusion(self):
        """EC1: Both --issue-key and --pr-id → exact error message."""
        with pytest.raises(
            ValueError,
            match="--issue-key and --pr-id are mutually exclusive. Provide one or neither.",
        ):
            resolve_analysis_context(issue_key="PROJ-1", pr_id=42)

    def test_ec2_empty_issue_key(self):
        """EC2: Empty --issue-key raises usage error."""
        with pytest.raises(ValueError, match="must not be empty"):
            resolve_analysis_context(issue_key="  ")

    def test_ec3_no_workflows_directory(self, tmp_path):
        """EC3: No .agdt/workflows/ → empty lists (code-only evidence)."""
        result = list_worktree_state_dirs(tmp_path, "PROJ-1")
        assert result == []

        logs = scan_identity_logs(tmp_path, "PROJ-1")
        assert logs == []

    def test_ec4_no_identity_directories(self, tmp_path):
        """EC4: Empty workflows dir → empty lists (code-only evidence)."""
        (tmp_path / ".agdt" / "workflows").mkdir(parents=True)

        result = list_worktree_state_dirs(tmp_path, "PROJ-1")
        assert result == []

    def test_ec6_static_only_returns_null(self, tmp_path):
        """EC6: --static-only with external worktrees → None."""
        result = collect_external_context(tmp_path, "PROJ-1", static_only=True)
        assert result is None

    def test_ec7_identity_dir_no_matching_logs_skipped(self, tmp_path):
        """EC7: Identity dir with no matching logs → skipped silently."""
        wf = tmp_path / ".agdt" / "workflows"
        (wf / "alice" / "OTHER-KEY" / "background-tasks" / "logs").mkdir(parents=True)

        result = scan_identity_logs(tmp_path, "PROJ-1")
        assert result == []
