"""Tests for _create_session helper function."""

from datetime import datetime, timezone

from agentic_devtools.cli.azure_devops.review_scaffold import _create_session
from agentic_devtools.cli.azure_devops.review_state import ReviewSession


class TestCreateSession:
    """Tests for _create_session."""

    def test_returns_review_session(self):
        """Returns a ReviewSession instance."""
        session = _create_session("gpt-5")
        assert isinstance(session, ReviewSession)

    def test_has_uuid_session_id(self):
        """Session ID is a non-empty hex UUID."""
        session = _create_session("gpt-5")
        assert len(session.sessionId) == 32
        int(session.sessionId, 16)  # validates hex

    def test_model_id_set(self):
        """Model ID matches the provided value."""
        session = _create_session("claude-4")
        assert session.modelId == "claude-4"

    def test_status_is_in_progress(self):
        """Initial status is 'in_progress'."""
        session = _create_session("gpt-5")
        assert session.status == "in_progress"

    def test_completed_utc_is_none(self):
        """completedUtc is None on creation."""
        session = _create_session("gpt-5")
        assert session.completedUtc is None

    def test_started_utc_set(self):
        """startedUtc is a non-empty ISO timestamp."""
        session = _create_session("gpt-5")
        assert session.startedUtc
        assert "T" in session.startedUtc

    def test_uses_injected_now(self):
        """Uses the injected now parameter for startedUtc."""
        fixed_time = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        session = _create_session("gpt-5", now=fixed_time)
        assert session.startedUtc == fixed_time.isoformat()

    def test_unique_session_ids(self):
        """Two sessions created at the same time have different IDs."""
        s1 = _create_session("gpt-5")
        s2 = _create_session("gpt-5")
        assert s1.sessionId != s2.sessionId

    def test_commit_hash_stored(self):
        """commit_hash is stored in the session."""
        session = _create_session("gpt-5", commit_hash="abc123def")
        assert session.commitHash == "abc123def"

    def test_commit_hash_defaults_to_none(self):
        """commit_hash defaults to None when not provided."""
        session = _create_session("gpt-5")
        assert session.commitHash is None
