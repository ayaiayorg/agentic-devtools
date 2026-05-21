"""Tests for ReviewSession dataclass."""

from agentic_devtools.cli.azure_devops.review_state import ReviewSession


class TestReviewSession:
    """Tests for ReviewSession dataclass."""

    def test_creation_with_defaults(self):
        """Test creation with minimal required fields and defaults."""
        s = ReviewSession(sessionId="abc-123", modelId="claude-4", startedUtc="2026-03-01T10:00:00Z")
        assert s.sessionId == "abc-123"
        assert s.modelId == "claude-4"
        assert s.startedUtc == "2026-03-01T10:00:00Z"
        assert s.completedUtc is None
        assert s.status == "pending"
        assert s.commitHash is None
        assert s.activityLogCommentId is None

    def test_creation_with_all_fields(self):
        """Test creation with all fields specified."""
        s = ReviewSession(
            sessionId="def-456",
            modelId="gpt-5",
            startedUtc="2026-03-01T10:00:00Z",
            completedUtc="2026-03-01T10:30:00Z",
            status="completed",
            commitHash="abc123def",
            activityLogCommentId=42,
        )
        assert s.sessionId == "def-456"
        assert s.modelId == "gpt-5"
        assert s.completedUtc == "2026-03-01T10:30:00Z"
        assert s.status == "completed"
        assert s.commitHash == "abc123def"
        assert s.activityLogCommentId == 42

    def test_to_dict(self):
        """Test serialization to dictionary."""
        s = ReviewSession(
            sessionId="abc-123",
            modelId="claude-4",
            startedUtc="2026-03-01T10:00:00Z",
            completedUtc="2026-03-01T10:30:00Z",
            status="completed",
            commitHash="abc123",
            activityLogCommentId=99,
        )
        d = s.to_dict()
        assert d == {
            "sessionId": "abc-123",
            "modelId": "claude-4",
            "startedUtc": "2026-03-01T10:00:00Z",
            "completedUtc": "2026-03-01T10:30:00Z",
            "status": "completed",
            "commitHash": "abc123",
            "activityLogCommentId": 99,
        }

    def test_to_dict_defaults(self):
        """Test serialization preserves default values."""
        s = ReviewSession(sessionId="abc-123", modelId="claude-4", startedUtc="2026-03-01T10:00:00Z")
        d = s.to_dict()
        assert d["completedUtc"] is None
        assert d["status"] == "pending"
        assert d["commitHash"] is None
        assert d["activityLogCommentId"] is None

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "sessionId": "abc-123",
            "modelId": "claude-4",
            "startedUtc": "2026-03-01T10:00:00Z",
            "completedUtc": "2026-03-01T10:30:00Z",
            "status": "completed",
            "commitHash": "abc123",
            "activityLogCommentId": 77,
        }
        s = ReviewSession.from_dict(data)
        assert s.sessionId == "abc-123"
        assert s.modelId == "claude-4"
        assert s.startedUtc == "2026-03-01T10:00:00Z"
        assert s.completedUtc == "2026-03-01T10:30:00Z"
        assert s.status == "completed"
        assert s.commitHash == "abc123"
        assert s.activityLogCommentId == 77

    def test_from_dict_defaults(self):
        """Test from_dict with missing optional fields uses defaults."""
        data = {
            "sessionId": "abc-123",
            "modelId": "claude-4",
            "startedUtc": "2026-03-01T10:00:00Z",
        }
        s = ReviewSession.from_dict(data)
        assert s.completedUtc is None
        assert s.status == "pending"
        assert s.commitHash is None
        assert s.activityLogCommentId is None

    def test_roundtrip(self):
        """Test to_dict/from_dict round-trips correctly."""
        original = ReviewSession(
            sessionId="abc-123",
            modelId="claude-4",
            startedUtc="2026-03-01T10:00:00Z",
            completedUtc="2026-03-01T10:30:00Z",
            status="completed",
            commitHash="abc123",
            activityLogCommentId=55,
        )
        restored = ReviewSession.from_dict(original.to_dict())
        assert restored.sessionId == original.sessionId
        assert restored.modelId == original.modelId
        assert restored.startedUtc == original.startedUtc
        assert restored.completedUtc == original.completedUtc
        assert restored.status == original.status
        assert restored.commitHash == original.commitHash
        assert restored.activityLogCommentId == original.activityLogCommentId

    def test_roundtrip_with_defaults(self):
        """Test round-trip with default values."""
        original = ReviewSession(sessionId="x", modelId="m", startedUtc="2026-01-01T00:00:00Z")
        restored = ReviewSession.from_dict(original.to_dict())
        assert restored.completedUtc is None
        assert restored.status == "pending"
        assert restored.activityLogCommentId is None

    def test_valid_status_values(self):
        """Test that all expected status values are accepted."""
        for status in ("pending", "in_progress", "completed", "failed"):
            s = ReviewSession(
                sessionId="x",
                modelId="m",
                startedUtc="2026-01-01T00:00:00Z",
                status=status,
            )
            assert s.status == status

    def test_engine_field_default_none(self):
        """Test engine field defaults to None."""
        s = ReviewSession(sessionId="x", modelId="m", startedUtc="2026-01-01T00:00:00Z")
        assert s.engine is None

    def test_to_dict_omits_engine_when_none(self):
        """Test to_dict does not include engine key when engine is None."""
        s = ReviewSession(sessionId="x", modelId="m", startedUtc="2026-01-01T00:00:00Z")
        d = s.to_dict()
        assert "engine" not in d

    def test_to_dict_includes_engine_when_set(self):
        """Test to_dict includes engine key when engine is not None."""
        s = ReviewSession(
            sessionId="x", modelId="m", startedUtc="2026-01-01T00:00:00Z", engine="langchain"
        )
        d = s.to_dict()
        assert d["engine"] == "langchain"

    def test_from_dict_with_engine(self):
        """Test from_dict correctly restores engine field."""
        data = {
            "sessionId": "x",
            "modelId": "m",
            "startedUtc": "2026-01-01T00:00:00Z",
            "engine": "langchain",
        }
        s = ReviewSession.from_dict(data)
        assert s.engine == "langchain"

    def test_roundtrip_with_engine(self):
        """Test round-trip preserves engine field."""
        original = ReviewSession(
            sessionId="x", modelId="m", startedUtc="2026-01-01T00:00:00Z", engine="langchain"
        )
        restored = ReviewSession.from_dict(original.to_dict())
        assert restored.engine == "langchain"
