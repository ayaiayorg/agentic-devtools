"""Tests for targeted_repair function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.finalization.models import EligibleComment
from agentic_devtools.cli.azure_devops.finalization.repair import targeted_repair
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewState,
)


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
    config.build_api_url.return_value = "https://api/url"
    return config


class TestTargetedRepair:
    """Tests for targeted_repair function."""

    def test_dry_run_skips_mutations(self):
        """Should not make API calls in dry-run mode."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
            file_path="/src/a.py",
        )
        result = targeted_repair(
            [comment],
            {1: "expected content"},
            _mock_config(),
            {},
            42,
            _minimal_review_state(),
            dry_run=True,
        )
        assert result.attempted == 1
        assert result.succeeded == 1

    def test_patches_non_converged_comment(self):
        """Should PATCH non-converged comments."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
            file_path="/src/a.py",
        )
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_requests.patch.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            result = targeted_repair(
                [comment],
                {1: "expected content"},
                _mock_config(),
                {},
                42,
                _minimal_review_state(),
            )
        assert result.succeeded == 1

    def test_handles_missing_expected_content(self):
        """Should fail gracefully when expected content is missing."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=99,
            marker_type="file-summary",
            marker_data={},
            current_content="old",
            file_path="/src/a.py",
        )
        result = targeted_repair(
            [comment],
            {},
            _mock_config(),
            {},
            42,
            _minimal_review_state(),
        )
        assert result.failed == 1
