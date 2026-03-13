"""Tests for save_applied_suggestions_state."""

import json
from unittest.mock import patch

from agentic_devtools.cli.workflows import applied_suggestions as as_module
from agentic_devtools.cli.workflows.applied_suggestions import (
    AppliedSuggestionEntry,
    AppliedSuggestionsState,
    save_applied_suggestions_state,
)


class TestSaveAppliedSuggestionsState:
    """Tests for save_applied_suggestions_state function."""

    def test_creates_file(self, tmp_path):
        """Test that save creates the JSON file."""
        with patch.object(as_module, "get_state_dir", return_value=tmp_path):
            state = AppliedSuggestionsState(prId=12345)
            save_applied_suggestions_state(state)

            expected = tmp_path / "apply-suggestions" / "applied-suggestions.json"
            assert expected.exists()

    def test_file_is_valid_json(self, tmp_path):
        """Test that the saved file is valid JSON."""
        with patch.object(as_module, "get_state_dir", return_value=tmp_path):
            state = AppliedSuggestionsState(prId=12345)
            save_applied_suggestions_state(state)

            expected = tmp_path / "apply-suggestions" / "applied-suggestions.json"
            data = json.loads(expected.read_text(encoding="utf-8"))
            assert data["prId"] == 12345

    def test_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created if they don't exist."""
        with patch.object(as_module, "get_state_dir", return_value=tmp_path):
            state = AppliedSuggestionsState(prId=99999)
            save_applied_suggestions_state(state)

            expected = tmp_path / "apply-suggestions" / "applied-suggestions.json"
            assert expected.exists()

    def test_overwrites_existing_file(self, tmp_path):
        """Test that saving again overwrites the existing file."""
        with patch.object(as_module, "get_state_dir", return_value=tmp_path):
            state = AppliedSuggestionsState(prId=100)
            save_applied_suggestions_state(state)

            state.prId = 200
            save_applied_suggestions_state(state)

            expected = tmp_path / "apply-suggestions" / "applied-suggestions.json"
            data = json.loads(expected.read_text(encoding="utf-8"))
            assert data["prId"] == 200

    def test_serializes_entries(self, tmp_path):
        """Test that entries are correctly serialized."""
        with patch.object(as_module, "get_state_dir", return_value=tmp_path):
            state = AppliedSuggestionsState(prId=100)
            state.add_entry("s1", "/src/app.ts", status="applied")
            save_applied_suggestions_state(state)

            expected = tmp_path / "apply-suggestions" / "applied-suggestions.json"
            data = json.loads(expected.read_text(encoding="utf-8"))
            assert len(data["entries"]) == 1
            assert data["entries"][0]["suggestionId"] == "s1"

    def test_serializes_review_snapshot(self, tmp_path):
        """Test that reviewStateSnapshot is serialized when present."""
        with patch.object(as_module, "get_state_dir", return_value=tmp_path):
            snapshot = {"prId": 100, "status": "needs-work"}
            state = AppliedSuggestionsState(
                prId=100,
                reviewStateSnapshot=snapshot,
            )
            save_applied_suggestions_state(state)

            expected = tmp_path / "apply-suggestions" / "applied-suggestions.json"
            data = json.loads(expected.read_text(encoding="utf-8"))
            assert data["reviewStateSnapshot"] == snapshot

    def test_calls_mark_dirty(self, tmp_path):
        """Test that save calls mark_dirty after writing."""
        from agentic_devtools.cli.git.agdt_branch import _reset_dirty, is_dirty

        _reset_dirty()
        try:
            with patch.object(as_module, "get_state_dir", return_value=tmp_path):
                state = AppliedSuggestionsState(prId=100)
                save_applied_suggestions_state(state)
                assert is_dirty() is True
        finally:
            _reset_dirty()

    def test_succeeds_when_mark_dirty_import_fails(self, tmp_path):
        """Test that save still writes when mark_dirty import fails."""
        import builtins

        original_import = builtins.__import__

        def failing_import(name, *args, **kwargs):
            if "agdt_branch" in name:
                raise ImportError("simulated")
            return original_import(name, *args, **kwargs)

        with patch.object(as_module, "get_state_dir", return_value=tmp_path):
            state = AppliedSuggestionsState(prId=100)
            with patch.object(builtins, "__import__", side_effect=failing_import):
                save_applied_suggestions_state(state)

            expected = tmp_path / "apply-suggestions" / "applied-suggestions.json"
            assert expected.exists()
            data = json.loads(expected.read_text(encoding="utf-8"))
            assert data["prId"] == 100

    def test_saved_data_is_deserializable(self, tmp_path):
        """Test that saved data can be read back correctly."""
        with patch.object(as_module, "get_state_dir", return_value=tmp_path):
            state = AppliedSuggestionsState(
                prId=555,
                entries=[
                    AppliedSuggestionEntry(
                        suggestionId="s1",
                        filePath="/src/app.ts",
                        status="applied",
                    )
                ],
            )
            save_applied_suggestions_state(state)

            expected = tmp_path / "apply-suggestions" / "applied-suggestions.json"
            data = json.loads(expected.read_text(encoding="utf-8"))
            restored = AppliedSuggestionsState.from_dict(data)
            assert restored.prId == 555
            assert len(restored.entries) == 1
