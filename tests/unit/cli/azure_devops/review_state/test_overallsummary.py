"""Tests for OverallSummary dataclass."""

from agentic_devtools.cli.azure_devops.review_state import OverallSummary, ReviewStatus


class TestOverallSummary:
    """Tests for OverallSummary dataclass."""

    def test_creation_with_defaults(self):
        """Test creation with default status."""
        s = OverallSummary(threadId=161000, commentId=1771800000)
        assert s.threadId == 161000
        assert s.commentId == 1771800000
        assert s.status == ReviewStatus.UNREVIEWED

    def test_creation_with_status(self):
        """Test creation with explicit status."""
        s = OverallSummary(threadId=1, commentId=2, status="approved")
        assert s.status == "approved"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        s = OverallSummary(threadId=161000, commentId=1771800000, status="in-progress")
        d = s.to_dict()
        assert d == {
            "threadId": 161000,
            "commentId": 1771800000,
            "status": "in-progress",
        }

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {"threadId": 161000, "commentId": 1771800000, "status": "approved"}
        s = OverallSummary.from_dict(data)
        assert s.threadId == 161000
        assert s.commentId == 1771800000
        assert s.status == "approved"

    def test_from_dict_defaults_status(self):
        """Test that missing status defaults to unreviewed."""
        data = {"threadId": 1, "commentId": 2}
        s = OverallSummary.from_dict(data)
        assert s.status == ReviewStatus.UNREVIEWED

    def test_roundtrip(self):
        """Test to_dict/from_dict round-trips correctly."""
        original = OverallSummary(threadId=5, commentId=10, status="needs-work")
        restored = OverallSummary.from_dict(original.to_dict())
        assert restored.threadId == 5
        assert restored.commentId == 10
        assert restored.status == "needs-work"
