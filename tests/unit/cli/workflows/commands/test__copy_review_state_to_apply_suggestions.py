"""Tests for _copy_review_state_to_apply_suggestions."""

import json
from unittest.mock import patch

from agentic_devtools import state
from agentic_devtools.cli.workflows import applied_suggestions as as_module
from agentic_devtools.cli.workflows.commands import (
    _copy_review_state_to_apply_suggestions,
)


class TestCopyReviewStateToApplySuggestions:
    """Tests for _copy_review_state_to_apply_suggestions helper."""

    def test_copies_review_state_into_applied_suggestions(self, tmp_path):
        """Test that review state is copied as a snapshot."""
        review_dir = tmp_path / "reviews"
        review_dir.mkdir()
        review_data = {"prId": 12345, "files": {"/src/app.ts": {"status": "needs-work"}}}
        (review_dir / "review-state.json").write_text(json.dumps(review_data), encoding="utf-8")

        with patch.object(state, "get_state_dir", return_value=tmp_path):
            with patch.object(as_module, "get_state_dir", return_value=tmp_path):
                with patch.object(state, "get_value", return_value="12345"):
                    _copy_review_state_to_apply_suggestions()

        applied_path = tmp_path / "apply-suggestions" / "applied-suggestions.json"
        assert applied_path.exists()
        data = json.loads(applied_path.read_text(encoding="utf-8"))
        assert data["prId"] == 12345
        assert data["reviewStateSnapshot"] == review_data

    def test_does_nothing_when_no_review_state(self, tmp_path):
        """Test that function is a no-op when review-state.json doesn't exist."""
        with patch.object(state, "get_state_dir", return_value=tmp_path):
            with patch.object(as_module, "get_state_dir", return_value=tmp_path):
                _copy_review_state_to_apply_suggestions()

        applied_path = tmp_path / "apply-suggestions" / "applied-suggestions.json"
        assert not applied_path.exists()

    def test_handles_invalid_json_gracefully(self, tmp_path):
        """Test that function handles corrupt review-state.json gracefully."""
        review_dir = tmp_path / "reviews"
        review_dir.mkdir()
        (review_dir / "review-state.json").write_text("not json", encoding="utf-8")

        with patch.object(state, "get_state_dir", return_value=tmp_path):
            with patch.object(as_module, "get_state_dir", return_value=tmp_path):
                _copy_review_state_to_apply_suggestions()

        applied_path = tmp_path / "apply-suggestions" / "applied-suggestions.json"
        assert not applied_path.exists()

    def test_pr_id_defaults_to_zero_when_missing(self, tmp_path):
        """Test that prId defaults to 0 when pull_request_id is not in state."""
        review_dir = tmp_path / "reviews"
        review_dir.mkdir()
        review_data = {"prId": 0}
        (review_dir / "review-state.json").write_text(json.dumps(review_data), encoding="utf-8")

        with patch.object(state, "get_state_dir", return_value=tmp_path):
            with patch.object(as_module, "get_state_dir", return_value=tmp_path):
                with patch.object(state, "get_value", return_value=None):
                    _copy_review_state_to_apply_suggestions()

        applied_path = tmp_path / "apply-suggestions" / "applied-suggestions.json"
        assert applied_path.exists()
        data = json.loads(applied_path.read_text(encoding="utf-8"))
        assert data["prId"] == 0
