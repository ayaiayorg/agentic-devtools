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


def _make_session(model_id="gpt-5", status="completed", started_hours_ago=0, commit_hash="abc123"):
    """Create a ReviewSession with a given age."""
    now = datetime.now(timezone.utc)
    started = now - timedelta(hours=started_hours_ago)
    return ReviewSession(
        sessionId="sess-1",
        modelId=model_id,
        startedUtc=started.isoformat(),
        completedUtc=now.isoformat() if status == "completed" else None,
        status=status,
        commitHash=commit_hash,
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
        """When both completed and in-progress sessions exist, returns 'already_reviewed' regardless of order."""
        sessions = [
            _make_session(status="in_progress", started_hours_ago=0),
            _make_session(status="completed"),
        ]
        # in_progress session is FIRST — completed should still take priority
        state = _make_state(sessions=[sessions[0], sessions[1]])
        result = _check_session_status(state, "abc123", "gpt-5")
        assert result == "already_reviewed"

    def test_failed_sessions_only_returns_first_review(self):
        """When only failed sessions exist for this model, returns 'first_review' (not 'different_model')."""
        session = _make_session(status="failed", started_hours_ago=3)
        state = _make_state(sessions=[session])
        result = _check_session_status(state, "abc123", "gpt-5")
        assert result == "first_review"

    def test_failed_sessions_with_other_model_returns_different_model(self):
        """Failed sessions for this model + active session for another model returns 'different_model'."""
        failed_session = ReviewSession(
            sessionId="s1",
            modelId="gpt-5",
            startedUtc="2026-01-01T00:00:00+00:00",
            status="failed",
            commitHash="abc123",
        )
        other_session = _make_session(model_id="claude-4", status="completed")
        state = _make_state(sessions=[failed_session, other_session])
        result = _check_session_status(state, "abc123", "gpt-5")
        assert result == "different_model"

    def test_multiple_stale_sessions_returns_resume_stale(self):
        """Multiple stale in-progress sessions still returns 'resume_stale'."""
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
        result = _check_session_status(state, "abc123", "gpt-5", now=now)
        assert result == "resume_stale"

    def test_old_sessions_from_prior_commit_do_not_trigger_different_model(self):
        """Sessions from a prior commit for another model should not trigger 'different_model'.

        After incremental re-scaffolding, old sessions remain in the list with
        their original commitHash. A new model arriving for the current commit
        should get 'first_review', not 'different_model'.
        """
        old_session = ReviewSession(
            sessionId="old-sess",
            modelId="claude-4",
            startedUtc="2026-01-01T00:00:00+00:00",
            completedUtc="2026-01-01T01:00:00+00:00",
            status="completed",
            commitHash="old_commit_aaa",
        )
        # State now has commitHash="abc123" (new commit), but old session is for "old_commit_aaa"
        state = _make_state(commit_hash="abc123", sessions=[old_session])
        result = _check_session_status(state, "abc123", "gemini-pro")
        assert result == "first_review"

    def test_current_commit_session_triggers_different_model(self):
        """A session for the current commit from another model triggers 'different_model'."""
        current_session = ReviewSession(
            sessionId="cur-sess",
            modelId="claude-4",
            startedUtc="2026-01-01T00:00:00+00:00",
            completedUtc="2026-01-01T01:00:00+00:00",
            status="completed",
            commitHash="abc123",
        )
        state = _make_state(commit_hash="abc123", sessions=[current_session])
        result = _check_session_status(state, "abc123", "gemini-pro")
        assert result == "different_model"
