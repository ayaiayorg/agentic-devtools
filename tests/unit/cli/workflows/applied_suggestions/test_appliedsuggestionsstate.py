"""Tests for AppliedSuggestionsState."""

from agentic_devtools.cli.workflows.applied_suggestions import (
    AppliedSuggestionEntry,
    AppliedSuggestionsState,
)


class TestAppliedSuggestionsState:
    """Tests for AppliedSuggestionsState dataclass."""

    def test_create_default(self):
        """Test creating state with defaults."""
        state = AppliedSuggestionsState()
        assert state.prId == 0
        assert state.entries == []
        assert state.reviewStateSnapshot is None

    def test_to_dict_minimal(self):
        """Test serialization without review snapshot."""
        state = AppliedSuggestionsState(prId=12345)
        result = state.to_dict()
        assert result == {"prId": 12345, "entries": []}
        assert "reviewStateSnapshot" not in result

    def test_to_dict_with_snapshot(self):
        """Test serialization with review snapshot."""
        snapshot = {"prId": 12345, "files": {}}
        state = AppliedSuggestionsState(
            prId=12345,
            reviewStateSnapshot=snapshot,
        )
        result = state.to_dict()
        assert result["reviewStateSnapshot"] == snapshot

    def test_to_dict_with_entries(self):
        """Test serialization with entries."""
        entry = AppliedSuggestionEntry(suggestionId="s1", filePath="/src/app.ts")
        state = AppliedSuggestionsState(prId=100, entries=[entry])
        result = state.to_dict()
        assert len(result["entries"]) == 1
        assert result["entries"][0]["suggestionId"] == "s1"

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "prId": 789,
            "entries": [
                {"suggestionId": "s1", "filePath": "/src/app.ts", "status": "applied"},
            ],
            "reviewStateSnapshot": {"prId": 789},
        }
        state = AppliedSuggestionsState.from_dict(data)
        assert state.prId == 789
        assert len(state.entries) == 1
        assert state.entries[0].suggestionId == "s1"
        assert state.reviewStateSnapshot == {"prId": 789}

    def test_from_dict_defaults(self):
        """Test deserialization with missing keys uses defaults."""
        data = {}
        state = AppliedSuggestionsState.from_dict(data)
        assert state.prId == 0
        assert state.entries == []
        assert state.reviewStateSnapshot is None

    def test_add_entry(self):
        """Test adding a new entry."""
        state = AppliedSuggestionsState(prId=100)
        entry = state.add_entry(
            suggestion_id="s1",
            file_path="/src/app.ts",
            status="applied",
            applied_utc="2024-01-01T00:00:00Z",
            notes="Done",
        )
        assert len(state.entries) == 1
        assert entry.suggestionId == "s1"
        assert entry.filePath == "/src/app.ts"
        assert entry.status == "applied"
        assert entry.appliedUtc == "2024-01-01T00:00:00Z"
        assert entry.notes == "Done"

    def test_add_multiple_entries(self):
        """Test adding multiple entries."""
        state = AppliedSuggestionsState(prId=100)
        state.add_entry("s1", "/file1.ts")
        state.add_entry("s2", "/file2.ts", status="skipped")
        assert len(state.entries) == 2

    def test_roundtrip(self):
        """Test that to_dict/from_dict round-trips correctly."""
        original = AppliedSuggestionsState(
            prId=999,
            entries=[
                AppliedSuggestionEntry(
                    suggestionId="s1",
                    filePath="/src/test.ts",
                    status="applied",
                )
            ],
            reviewStateSnapshot={"prId": 999, "status": "needs-work"},
        )
        restored = AppliedSuggestionsState.from_dict(original.to_dict())
        assert restored.prId == original.prId
        assert len(restored.entries) == 1
        assert restored.entries[0].suggestionId == "s1"
        assert restored.reviewStateSnapshot == {"prId": 999, "status": "needs-work"}
