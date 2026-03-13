"""Tests for AppliedSuggestionEntry."""

from agentic_devtools.cli.workflows.applied_suggestions import (
    AppliedSuggestionEntry,
)


class TestAppliedSuggestionEntry:
    """Tests for AppliedSuggestionEntry dataclass."""

    def test_create_default(self):
        """Test creating entry with defaults."""
        entry = AppliedSuggestionEntry(suggestionId="s1", filePath="/src/app.ts")
        assert entry.suggestionId == "s1"
        assert entry.filePath == "/src/app.ts"
        assert entry.status == "applied"
        assert entry.appliedUtc == ""
        assert entry.notes == ""

    def test_to_dict(self):
        """Test serialization to dict."""
        entry = AppliedSuggestionEntry(
            suggestionId="s1",
            filePath="/src/app.ts",
            status="skipped",
            appliedUtc="2024-01-01T00:00:00Z",
            notes="Not applicable",
        )
        result = entry.to_dict()
        assert result == {
            "suggestionId": "s1",
            "filePath": "/src/app.ts",
            "status": "skipped",
            "appliedUtc": "2024-01-01T00:00:00Z",
            "notes": "Not applicable",
        }

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "suggestionId": "s2",
            "filePath": "/src/utils.ts",
            "status": "deferred",
            "appliedUtc": "2024-06-15T12:00:00Z",
            "notes": "Deferred to next sprint",
        }
        entry = AppliedSuggestionEntry.from_dict(data)
        assert entry.suggestionId == "s2"
        assert entry.filePath == "/src/utils.ts"
        assert entry.status == "deferred"

    def test_from_dict_defaults(self):
        """Test deserialization with missing keys uses defaults."""
        data = {}
        entry = AppliedSuggestionEntry.from_dict(data)
        assert entry.suggestionId == ""
        assert entry.filePath == ""
        assert entry.status == "applied"
        assert entry.appliedUtc == ""
        assert entry.notes == ""

    def test_roundtrip(self):
        """Test that to_dict/from_dict round-trips correctly."""
        original = AppliedSuggestionEntry(
            suggestionId="s3",
            filePath="/src/test.ts",
            status="applied",
            appliedUtc="2024-12-01T10:00:00Z",
            notes="Applied as-is",
        )
        restored = AppliedSuggestionEntry.from_dict(original.to_dict())
        assert restored.suggestionId == original.suggestionId
        assert restored.filePath == original.filePath
        assert restored.status == original.status
        assert restored.appliedUtc == original.appliedUtc
        assert restored.notes == original.notes
