"""Tests for _compute_activity_log_content function."""

from agentic_devtools.cli.azure_devops.finalization.convergence import _compute_activity_log_content
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewSession,
    ReviewState,
)


def _minimal_review_state(sessions=None, commit_hash="abc123def456"):
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
        commitHash=commit_hash,
    )


class TestComputeActivityLogContent:
    """Tests for _compute_activity_log_content function."""

    def test_returns_empty_when_no_sessions(self):
        """Should return empty string when review_state has no sessions."""
        result = _compute_activity_log_content(_minimal_review_state(sessions=[]))
        assert result == ""

    def test_renders_completed_session(self):
        """Should render activity log entry for completed session."""
        session = ReviewSession(
            sessionId="sess-1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            completedUtc="2026-01-01T01:00:00+00:00",
            status="completed",
        )
        result = _compute_activity_log_content(_minimal_review_state(sessions=[session]))
        assert "✅ Completed" in result
        assert "Review session completed successfully." in result

    def test_uses_commit_hash_short(self):
        """Should use short commit hash in output."""
        session = ReviewSession(
            sessionId="sess-1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="in_progress",
        )
        result = _compute_activity_log_content(
            _minimal_review_state(sessions=[session], commit_hash="abcdef1234567890")
        )
        assert "abcdef1" in result

    def test_uses_unknown_when_no_commit_hash(self):
        """Should use 'unknown' when commitHash is None."""
        session = ReviewSession(
            sessionId="sess-1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="in_progress",
        )
        result = _compute_activity_log_content(_minimal_review_state(sessions=[session], commit_hash=None))
        assert "unknown" in result

    def test_uses_latest_session(self):
        """Should use the last session in the list."""
        s1 = ReviewSession(
            sessionId="sess-1",
            modelId="model-a",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="completed",
        )
        s2 = ReviewSession(
            sessionId="sess-2",
            modelId="model-b",
            startedUtc="2026-01-02T00:00:00+00:00",
            status="in_progress",
        )
        result = _compute_activity_log_content(_minimal_review_state(sessions=[s1, s2]))
        assert "model-b" in result

    def test_strips_marker_line(self):
        """Should return body only without marker line."""
        session = ReviewSession(
            sessionId="sess-1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="completed",
        )
        result = _compute_activity_log_content(_minimal_review_state(sessions=[session]))
        # Should not contain the HTML comment marker
        assert "<!-- agdt-review" not in result
