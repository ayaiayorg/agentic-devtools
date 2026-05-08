"""Tests for run_finalization_pass orchestrator function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.finalization.models import FinalizationReport
from agentic_devtools.cli.azure_devops.finalization.orchestrator import run_finalization_pass
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewState,
)


def _minimal_review_state():
    """Build a minimal ReviewState."""
    return ReviewState(
        prId=42,
        repoId="repo-guid",
        repoName="test-repo",
        project="TestProject",
        organization="https://dev.azure.com/org",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00+00:00",
        overallSummary=OverallSummary(threadId=100, commentId=1, status="approved"),
        folders={"src": FolderGroup(files=["/src/a.py"])},
        files={"/src/a.py": FileEntry(threadId=10, commentId=1, folder="src", fileName="a.py", status="approved")},
    )


def _mock_config():
    config = MagicMock()
    config.organization = "https://dev.azure.com/org"
    config.build_api_url.return_value = "https://api/threads"
    return config


class TestRunFinalizationPass:
    """Tests for run_finalization_pass function."""

    def test_returns_skipped_when_identity_fails(self, temp_state_dir):
        """Should return skipped status when PAT identity cannot be resolved."""
        with patch(
            "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
            return_value=None,
        ):
            result = run_finalization_pass(
                _minimal_review_state(),
                42,
                _mock_config(),
                {},
                dry_run=False,
            )
        assert isinstance(result, FinalizationReport)
        assert result.status == "skipped"

    def test_returns_skipped_when_threads_fail(self, temp_state_dir):
        """Should return skipped when thread fetching fails."""
        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=None,
            ),
        ):
            result = run_finalization_pass(
                _minimal_review_state(),
                42,
                _mock_config(),
                {},
            )
        assert result.status == "skipped"

    def test_returns_noop_when_no_eligible_comments(self, temp_state_dir):
        """Should return no-op when no eligible comments found."""
        from agentic_devtools.cli.azure_devops.finalization.models import EligibleComments

        with (
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
                return_value="user-guid",
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator._fetch_threads",
                return_value=[],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.finalization.orchestrator.classify_eligible_comments",
                return_value=EligibleComments(),
            ),
        ):
            result = run_finalization_pass(
                _minimal_review_state(),
                42,
                _mock_config(),
                {},
            )
        assert result.status == "no-op"

    def test_non_blocking_on_exception(self, temp_state_dir):
        """Should catch exceptions and return failure report."""
        with patch(
            "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
            side_effect=RuntimeError("unexpected"),
        ):
            result = run_finalization_pass(
                _minimal_review_state(),
                42,
                _mock_config(),
                {},
            )
        assert result.status == "failure"
        assert any("unexpected" in d for d in result.details)

    def test_missing_review_state_returns_report(self, temp_state_dir):
        """Should handle review state gracefully and return a report."""
        # The orchestrator always receives review_state as a parameter,
        # so this tests the exception path
        with patch(
            "agentic_devtools.cli.azure_devops.finalization.orchestrator.resolve_pat_identity",
            side_effect=Exception("state issue"),
        ):
            result = run_finalization_pass(
                _minimal_review_state(),
                42,
                _mock_config(),
                {},
            )
        assert isinstance(result, FinalizationReport)
