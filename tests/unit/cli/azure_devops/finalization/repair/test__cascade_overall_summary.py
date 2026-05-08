"""Tests for _cascade_overall_summary function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.finalization.repair import _cascade_overall_summary
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewState,
)

_BASE_URL = "https://dev.azure.com/org/proj/_git/repo/pullRequest/42"


def _minimal_review_state():
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
    config.build_api_url.return_value = "https://api/url"
    return config


class TestCascadeOverallSummary:
    """Tests for _cascade_overall_summary function."""

    def test_calls_execute_cascade(self):
        """Should call execute_cascade with patch operations."""
        with (
            patch(
                "agentic_devtools.cli.azure_devops.status_cascade.cascade_overall_summary_update",
                return_value=[],
            ) as mock_cascade_update,
            patch(
                "agentic_devtools.cli.azure_devops.status_cascade.execute_cascade",
            ) as mock_execute,
        ):
            _cascade_overall_summary(
                _minimal_review_state(),
                _mock_config(),
                {"Authorization": "Bearer token"},
                42,
                _BASE_URL,
            )
        mock_cascade_update.assert_called_once()
        mock_execute.assert_called_once()

    def test_passes_repo_id_and_pr_id(self):
        """Should pass correct repo_id and pr_id to execute_cascade."""
        with (
            patch(
                "agentic_devtools.cli.azure_devops.status_cascade.cascade_overall_summary_update",
                return_value=[],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.status_cascade.execute_cascade",
            ) as mock_execute,
        ):
            _cascade_overall_summary(
                _minimal_review_state(),
                _mock_config(),
                {},
                42,
                _BASE_URL,
            )
        call_kwargs = mock_execute.call_args[1]
        assert call_kwargs["repo_id"] == "repo-guid"
        assert call_kwargs["pull_request_id"] == 42
