"""Tests for batch_repair_pass function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.finalization.models import EligibleComment, EligibleComments
from agentic_devtools.cli.azure_devops.finalization.repair import batch_repair_pass
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
        files={
            "/src/a.py": FileEntry(
                threadId=10,
                commentId=1,
                folder="src",
                fileName="a.py",
                status="approved",
                summary="LGTM",
            ),
        },
    )


def _mock_config():
    config = MagicMock()
    config.organization = "https://dev.azure.com/org"
    config.build_api_url.return_value = "https://api/url"
    return config


class TestBatchRepairPass:
    """Tests for batch_repair_pass function."""

    def test_dry_run_skips_mutations(self):
        """Should not make API calls in dry-run mode."""
        eligible = EligibleComments(
            file_summaries=[
                EligibleComment(
                    thread_id=10,
                    comment_id=1,
                    marker_type="file-summary",
                    marker_data={"type": "file-summary", "file": "/src/a.py"},
                    current_content="old",
                    file_path="/src/a.py",
                )
            ],
        )
        result = batch_repair_pass(
            eligible,
            _minimal_review_state(),
            _mock_config(),
            {},
            42,
            _BASE_URL,
            dry_run=True,
        )
        assert result.attempted == 1
        assert result.succeeded == 1
        assert result.failed == 0

    def test_patches_file_summary(self):
        """Should PATCH file summary comments."""
        eligible = EligibleComments(
            file_summaries=[
                EligibleComment(
                    thread_id=10,
                    comment_id=1,
                    marker_type="file-summary",
                    marker_data={"type": "file-summary", "file": "/src/a.py"},
                    current_content="old",
                    file_path="/src/a.py",
                )
            ],
        )
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_requests.patch.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            result = batch_repair_pass(
                eligible,
                _minimal_review_state(),
                _mock_config(),
                {},
                42,
                _BASE_URL,
            )
        assert result.succeeded == 1
        assert result.failed == 0

    def test_catches_api_errors(self):
        """Should catch API errors and continue."""
        eligible = EligibleComments(
            file_summaries=[
                EligibleComment(
                    thread_id=10,
                    comment_id=1,
                    marker_type="file-summary",
                    marker_data={"type": "file-summary", "file": "/src/a.py"},
                    current_content="old",
                    file_path="/src/a.py",
                )
            ],
        )
        mock_requests = MagicMock()
        mock_requests.patch.side_effect = Exception("API error")

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            result = batch_repair_pass(
                eligible,
                _minimal_review_state(),
                _mock_config(),
                {},
                42,
                _BASE_URL,
            )
        assert result.failed == 1
        assert len(result.errors) == 1
