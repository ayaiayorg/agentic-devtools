"""Tests for _check_session_status helper function."""

from datetime import datetime, timedelta, timezone

from agentic_devtools.cli.azure_devops.review_scaffold import (
    STALE_SESSION_THRESHOLD,
    _check_session_status,
)
from agentic_devtools.cli.azure_devops.review_state import (
    FolderGroup,
    OverallSummary,
    ReviewSession,
    ReviewState,
)


def _make_state(commit_hash="abc123", sessions=None, model_id="gpt-5"):
    """Create a minimal ReviewState for testing."""
    return ReviewState(
        prId=1,
        repoId="repo-id",
        repoName="repo",
        project="proj",
        organization="org",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00+00:00",
        overallSummary=OverallSummary(threadId=100, commentId=1),
        folders={"src": FolderGroup(files=["/src/a.ts"])},
        commitHash=commit_hash,
        modelId=model_id,
        sessions=sessions or [],
    )


def _make_session(model_id="gpt-5", status="completed", started_hours_ago=0):
    """Create a ReviewSession with a given age."""
    now = datetime.now(timezone.utc)
    started = now - timedelta(hours=started_hours_ago)
    return ReviewSession(
        sessionId="sess-1",
        modelId=model_id,
        startedUtc=started.isoformat(),
        completedUtc=now.isoformat() if status == "completed" else None,
        status=status,
    )


class TestCheckSessionStatus:
    """Tests for _check_session_status."""

    def test_first_review_when_no_sessions(self):
        """Returns 'first_review' when no sessions exist for the commit."""
        state = _make_state(sessions=[])
        result = _check_session_status(state, "abc123", "gpt-5")
        assert result == "first_review"

    def test_already_reviewed_when_completed_session(self):
        """Returns 'already_reviewed' when a completed session exists."""
        session = _make_session(status="completed")
        state = _make_state(sessions=[session])
        result = _check_session_status(state, "abc123", "gpt-5")
        assert result == "already_reviewed"

    def test_in_progress_when_recent_session(self):
        """Returns 'in_progress' when a recent in-progress session exists."""
        session = _make_session(status="in_progress", started_hours_ago=0)
        state = _make_state(sessions=[session])
        now = datetime.now(timezone.utc)
        result = _check_session_status(state, "abc123", "gpt-5", now=now)
        assert result == "in_progress"

    def test_resume_stale_when_old_in_progress(self):
        """Returns 'resume_stale' when in-progress session is older than threshold."""
        session = _make_session(status="in_progress", started_hours_ago=3)
        state = _make_state(sessions=[session])
        now = datetime.now(timezone.utc)
        result = _check_session_status(state, "abc123", "gpt-5", now=now)
        assert result == "resume_stale"

    def test_different_model_when_other_models_have_sessions(self):
        """Returns 'different_model' when sessions exist but not for this model."""
        session = _make_session(model_id="claude-4", status="completed")
        state = _make_state(sessions=[session])
        result = _check_session_status(state, "abc123", "gpt-5")
        assert result == "different_model"

    def test_different_commit_when_hashes_differ(self):
        """Returns 'different_commit' when commit hashes differ."""
        state = _make_state(commit_hash="abc123")
        result = _check_session_status(state, "def456", "gpt-5")
        assert result == "different_commit"

    def test_none_commit_hashes_match(self):
        """Returns 'first_review' when both commit hashes are None."""
        state = _make_state(commit_hash=None)
        result = _check_session_status(state, None, "gpt-5")
        assert result == "first_review"

    def test_stale_threshold_boundary_not_stale(self):
        """Session just under the threshold is not stale."""
        now = datetime.now(timezone.utc)
        started = now - STALE_SESSION_THRESHOLD + timedelta(minutes=1)
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc=started.isoformat(),
            status="in_progress",
        )
        state = _make_state(sessions=[session])
        result = _check_session_status(state, "abc123", "gpt-5", now=now)
        assert result == "in_progress"

    def test_stale_threshold_boundary_is_stale(self):
        """Session exactly at the threshold is stale."""
        now = datetime.now(timezone.utc)
        started = now - STALE_SESSION_THRESHOLD
        session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc=started.isoformat(),
            status="in_progress",
        )
        state = _make_state(sessions=[session])
        result = _check_session_status(state, "abc123", "gpt-5", now=now)
        assert result == "resume_stale"

    def test_completed_takes_priority_over_in_progress(self):
        """When both completed and in-progress sessions exist, returns 'already_reviewed'."""
        sessions = [
            _make_session(status="in_progress", started_hours_ago=0),
            _make_session(status="completed"),
        ]
        # completed session is first in iteration, so it should return already_reviewed
        state = _make_state(sessions=[sessions[1], sessions[0]])
        result = _check_session_status(state, "abc123", "gpt-5")
        assert result == "already_reviewed"
