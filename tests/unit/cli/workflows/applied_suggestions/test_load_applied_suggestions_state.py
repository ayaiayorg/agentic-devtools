"""Tests for load_applied_suggestions_state."""

import json
from unittest.mock import patch

from agentic_devtools import state as state_module
from agentic_devtools.cli.workflows.applied_suggestions import (
    AppliedSuggestionsState,
    load_applied_suggestions_state,
    save_applied_suggestions_state,
)

_MOD = "agentic_devtools.cli.workflows.applied_suggestions"


class TestLoadAppliedSuggestionsState:
    """Tests for load_applied_suggestions_state function."""

    def test_loads_from_file(self, tmp_path):
        """Test loading from a valid local file."""
        with patch.object(state_module, "get_state_dir", return_value=tmp_path):
            # Write state
            state = AppliedSuggestionsState(prId=100)
            save_applied_suggestions_state(state)

            # Read it back
            result = load_applied_suggestions_state(fallback_to_branch=False)

        assert result is not None
        assert result.prId == 100

    def test_returns_none_when_no_file(self, tmp_path):
        """Test returns None when no file exists and branch fallback is off."""
        with patch.object(state_module, "get_state_dir", return_value=tmp_path):
            result = load_applied_suggestions_state(fallback_to_branch=False)
        assert result is None

    def test_returns_none_on_invalid_json(self, tmp_path):
        """Test returns None when file contains invalid JSON."""
        with patch.object(state_module, "get_state_dir", return_value=tmp_path):
            file_path = tmp_path / "apply-suggestions" / "applied-suggestions.json"
            file_path.parent.mkdir(parents=True)
            file_path.write_text("not valid json", encoding="utf-8")

            result = load_applied_suggestions_state(fallback_to_branch=False)
        assert result is None

    def test_loads_with_entries(self, tmp_path):
        """Test loading state that has entries."""
        with patch.object(state_module, "get_state_dir", return_value=tmp_path):
            data = {
                "prId": 200,
                "entries": [
                    {"suggestionId": "s1", "filePath": "/src/app.ts", "status": "applied"},
                ],
            }
            file_path = tmp_path / "apply-suggestions" / "applied-suggestions.json"
            file_path.parent.mkdir(parents=True)
            file_path.write_text(json.dumps(data), encoding="utf-8")

            result = load_applied_suggestions_state(fallback_to_branch=False)

        assert result is not None
        assert result.prId == 200
        assert len(result.entries) == 1
        assert result.entries[0].suggestionId == "s1"

    def test_loads_with_review_snapshot(self, tmp_path):
        """Test loading state that includes a review state snapshot."""
        with patch.object(state_module, "get_state_dir", return_value=tmp_path):
            data = {
                "prId": 300,
                "entries": [],
                "reviewStateSnapshot": {"prId": 300, "status": "needs-work"},
            }
            file_path = tmp_path / "apply-suggestions" / "applied-suggestions.json"
            file_path.parent.mkdir(parents=True)
            file_path.write_text(json.dumps(data), encoding="utf-8")

            result = load_applied_suggestions_state(fallback_to_branch=False)

        assert result is not None
        assert result.reviewStateSnapshot == {"prId": 300, "status": "needs-work"}

    @patch(
        f"{_MOD}._load_from_branch",
        return_value={"prId": 500, "entries": []},
    )
    def test_branch_fallback_returns_state(self, mock_branch, tmp_path):
        """Test that branch fallback returns state when local file missing."""
        with patch.object(state_module, "get_state_dir", return_value=tmp_path):
            result = load_applied_suggestions_state(
                fallback_to_branch=True,
                source_branch="feature/TEST-1",
                worktree_key="TEST-1",
            )
        assert result is not None
        assert result.prId == 500
        mock_branch.assert_called_once()

    @patch(f"{_MOD}._load_from_branch", return_value=None)
    def test_branch_fallback_returns_none(self, mock_branch, tmp_path):
        """Test returns None when branch fallback also finds nothing."""
        with patch.object(state_module, "get_state_dir", return_value=tmp_path):
            result = load_applied_suggestions_state(
                fallback_to_branch=True,
                source_branch="feature/TEST-1",
                worktree_key="TEST-1",
            )
        assert result is None
