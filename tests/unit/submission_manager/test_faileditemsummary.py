"""Tests for agentic_devtools.submission_manager.FailedItemSummary."""

from agentic_devtools.submission_manager import FailedItemSummary


class TestFailedItemSummary:
    """Tests for FailedItemSummary dataclass."""

    def test_creation(self):
        """Test creating a FailedItemSummary with all fields."""
        summary = FailedItemSummary(
            item_id="abc-123",
            file_path="/src/app.ts",
            last_error="429 Too Many Requests",
            attempts=4,
        )
        assert summary.item_id == "abc-123"
        assert summary.file_path == "/src/app.ts"
        assert summary.last_error == "429 Too Many Requests"
        assert summary.attempts == 4

    def test_to_dict(self):
        """Test to_dict returns correct structure."""
        summary = FailedItemSummary(
            item_id="id-1",
            file_path="/file.ts",
            last_error="timeout",
            attempts=3,
        )
        d = summary.to_dict()
        assert d == {
            "item_id": "id-1",
            "file_path": "/file.ts",
            "last_error": "timeout",
            "attempts": 3,
        }
