"""Tests for ActivityLogEntry.to_dict() and from_dict()."""

from agentic_devtools.cli.activity_log import ActivityLogEntry


class TestActivityLogEntry:
    """Tests for ActivityLogEntry dataclass serialization."""

    def test_to_dict_serializes_all_fields(self):
        """Test that to_dict produces a dictionary with all fields."""
        entry = ActivityLogEntry(
            postedUtc="2026-03-13T10:00:00Z",
            branchName="feature/DFLY-1234",
            worktreeKey="DFLY-1234",
            prCommentPosted=True,
            jiraCommentPosted=False,
            prId=42,
        )
        result = entry.to_dict()

        assert result == {
            "postedUtc": "2026-03-13T10:00:00Z",
            "branchName": "feature/DFLY-1234",
            "worktreeKey": "DFLY-1234",
            "prCommentPosted": True,
            "jiraCommentPosted": False,
            "prId": 42,
        }

    def test_from_dict_deserializes_all_fields(self):
        """Test that from_dict creates an entry with all fields."""
        data = {
            "postedUtc": "2026-03-13T10:00:00Z",
            "branchName": "feature/DFLY-1234",
            "worktreeKey": "DFLY-1234",
            "prCommentPosted": True,
            "jiraCommentPosted": True,
            "prId": 99,
        }
        entry = ActivityLogEntry.from_dict(data)

        assert entry.postedUtc == "2026-03-13T10:00:00Z"
        assert entry.branchName == "feature/DFLY-1234"
        assert entry.worktreeKey == "DFLY-1234"
        assert entry.prCommentPosted is True
        assert entry.jiraCommentPosted is True
        assert entry.prId == 99

    def test_round_trip_preserves_data(self):
        """Test that to_dict → from_dict round-trip preserves all data."""
        original = ActivityLogEntry(
            postedUtc="2026-01-01T00:00:00Z",
            branchName="fix/bug-456",
            worktreeKey="bug-456",
            prCommentPosted=False,
            jiraCommentPosted=True,
            prId=123,
        )
        restored = ActivityLogEntry.from_dict(original.to_dict())

        assert restored.postedUtc == original.postedUtc
        assert restored.branchName == original.branchName
        assert restored.worktreeKey == original.worktreeKey
        assert restored.prCommentPosted == original.prCommentPosted
        assert restored.jiraCommentPosted == original.jiraCommentPosted
        assert restored.prId == original.prId

    def test_from_dict_with_pr_id_none(self):
        """Test that from_dict defaults prId to None when missing."""
        data = {
            "postedUtc": "2026-03-13T10:00:00Z",
            "branchName": "feature/X",
            "worktreeKey": "X",
            "prCommentPosted": False,
            "jiraCommentPosted": False,
        }
        entry = ActivityLogEntry.from_dict(data)

        assert entry.prId is None

    def test_from_dict_with_pr_id_integer(self):
        """Test that from_dict correctly reads an integer prId."""
        data = {
            "postedUtc": "2026-03-13T10:00:00Z",
            "branchName": "feature/X",
            "worktreeKey": "X",
            "prCommentPosted": False,
            "jiraCommentPosted": False,
            "prId": 555,
        }
        entry = ActivityLogEntry.from_dict(data)

        assert entry.prId == 555

    def test_to_dict_with_pr_id_none(self):
        """Test that to_dict serializes prId as None."""
        entry = ActivityLogEntry(
            postedUtc="2026-03-13T10:00:00Z",
            branchName="feature/X",
            worktreeKey="X",
            prCommentPosted=False,
            jiraCommentPosted=False,
        )
        result = entry.to_dict()

        assert result["prId"] is None
