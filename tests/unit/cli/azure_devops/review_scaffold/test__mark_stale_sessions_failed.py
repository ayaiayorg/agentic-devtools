"""Tests for _mark_stale_sessions_failed helper function."""

from datetime import datetime, timedelta, timezone

from agentic_devtools.cli.azure_devops.review_scaffold import _mark_stale_sessions_failed
from agentic_devtools.cli.azure_devops.review_state import (
    OverallSummary,
    ReviewSession,
    ReviewState,
)


def _make_state(commit_hash="abc123", sessions=None):
    return ReviewState(
        prId=1,
        repoId="repo-id",
        repoName="repo",
        project="proj",
        organization="org",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00+00:00",
        overallSummary=OverallSummary(threadId=100, commentId=1),
        folders={},
        commitHash=commit_hash,
        sessions=sessions or [],
    )


class TestMarkStaleSessionsFailed:
    """Tests for _mark_stale_sessions_failed."""

    def test_marks_stale_in_progress_as_failed(self):
        """Marks stale in-progress sessions as failed."""
        now = datetime.now(timezone.utc)
        stale_started = now - timedelta(hours=3)
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc=stale_started.isoformat(),
            status="in_progress",
        )
        state = _make_state(sessions=[session])

        _mark_stale_sessions_failed(state, "abc123", "gpt-5", now=now)

        assert session.status == "failed"
        assert session.completedUtc is not None

    def test_does_not_mark_recent_session(self):
        """Does not mark recent in-progress sessions as failed."""
        now = datetime.now(timezone.utc)
        recent_started = now - timedelta(minutes=30)
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc=recent_started.isoformat(),
            status="in_progress",
        )
        state = _make_state(sessions=[session])

        _mark_stale_sessions_failed(state, "abc123", "gpt-5", now=now)

        assert session.status == "in_progress"
        assert session.completedUtc is None

    def test_does_not_mark_different_model(self):
        """Does not mark sessions from a different model."""
        now = datetime.now(timezone.utc)
        stale_started = now - timedelta(hours=3)
        session = ReviewSession(
            sessionId="s1",
            modelId="claude-4",
            startedUtc=stale_started.isoformat(),
            status="in_progress",
        )
        state = _make_state(sessions=[session])

        _mark_stale_sessions_failed(state, "abc123", "gpt-5", now=now)

        assert session.status == "in_progress"

    def test_does_not_mark_completed_session(self):
        """Does not mark already completed sessions."""
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="completed",
            completedUtc="2026-01-01T01:00:00+00:00",
        )
        state = _make_state(sessions=[session])

        _mark_stale_sessions_failed(state, "abc123", "gpt-5")

        assert session.status == "completed"

    def test_marks_multiple_stale_sessions(self):
        """Marks all stale sessions for the same commit+model."""
        now = datetime.now(timezone.utc)
        stale_started = now - timedelta(hours=3)
        s1 = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc=stale_started.isoformat(),
            status="in_progress",
        )
        s2 = ReviewSession(
            sessionId="s2",
            modelId="gpt-5",
            startedUtc=stale_started.isoformat(),
            status="in_progress",
        )
        state = _make_state(sessions=[s1, s2])

        _mark_stale_sessions_failed(state, "abc123", "gpt-5", now=now)

        assert s1.status == "failed"
        assert s2.status == "failed"

    def test_does_not_mark_different_commit(self):
        """Does not mark sessions when commit hash doesn't match."""
        now = datetime.now(timezone.utc)
        stale_started = now - timedelta(hours=3)
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc=stale_started.isoformat(),
            status="in_progress",
        )
        state = _make_state(commit_hash="abc123", sessions=[session])

        _mark_stale_sessions_failed(state, "different_hash", "gpt-5", now=now)

        assert session.status == "in_progress"
