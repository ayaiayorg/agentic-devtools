"""Tests for compute_expected_content function."""

from agentic_devtools.cli.azure_devops.finalization.convergence import compute_expected_content
from agentic_devtools.cli.azure_devops.finalization.models import EligibleComment
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewSession,
    ReviewState,
)

_BASE_URL = "https://dev.azure.com/org/proj/_git/repo/pullRequest/42"


def _minimal_review_state(sessions=None):
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
        sessions=sessions or [],
        commitHash="abc123def456",
    )


class TestComputeExpectedContent:
    """Tests for compute_expected_content."""

    def test_file_summary_renders_approved_content(self):
        """Should render file summary for an approved file."""
        comment = EligibleComment(
            thread_id=10,
            comment_id=1,
            marker_type="file-summary",
            marker_data={"type": "file-summary", "file": "/src/a.py"},
            current_content="old content",
            file_path="/src/a.py",
        )
        result = compute_expected_content(comment, _minimal_review_state(), _BASE_URL)
        assert "File Review Summary" in result
        assert "a.py" in result

    def test_overall_summary_renders(self):
        """Should render overall summary content."""
        comment = EligibleComment(
            thread_id=100,
            comment_id=1,
            marker_type="overall-summary",
            marker_data={"type": "overall-summary"},
            current_content="old content",
        )
        result = compute_expected_content(comment, _minimal_review_state(), _BASE_URL)
        assert "Overall PR Review Summary" in result

    def test_activity_log_renders_completed(self):
        """Should render activity log entry with completed status."""
        session = ReviewSession(
            sessionId="sess-1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            completedUtc="2026-01-01T01:00:00+00:00",
            status="completed",
        )
        comment = EligibleComment(
            thread_id=200,
            comment_id=2,
            marker_type="activity-log-entry",
            marker_data={"type": "activity-log-entry"},
            current_content="old content",
        )
        result = compute_expected_content(comment, _minimal_review_state(sessions=[session]), _BASE_URL)
        assert "✅ Completed" in result
        assert "Review session completed successfully." in result

    def test_returns_empty_for_unknown_type(self):
        """Should return empty string for unknown marker type."""
        comment = EligibleComment(
            thread_id=1,
            comment_id=1,
            marker_type="unknown",
            marker_data={},
            current_content="content",
        )
        result = compute_expected_content(comment, _minimal_review_state(), _BASE_URL)
        assert result == ""
