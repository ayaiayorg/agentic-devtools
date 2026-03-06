"""Tests for save_review_state function."""

import json
from unittest.mock import patch

from agentic_devtools.cli.azure_devops import review_state as rs_module
from agentic_devtools.cli.azure_devops.review_state import OverallSummary, ReviewState, save_review_state


def _make_review_state(pr_id: int = 25365) -> ReviewState:
    return ReviewState(
        prId=pr_id,
        repoId="repo-guid",
        repoName="dfly-platform-management",
        project="DragonflyMgmt",
        organization="https://dev.azure.com/swica",
        latestIterationId=5,
        scaffoldedUtc="2026-02-25T10:00:00Z",
        overallSummary=OverallSummary(threadId=161000, commentId=1771800000),
    )


class TestSaveReviewState:
    """Tests for save_review_state function."""

    def test_creates_file(self, tmp_path):
        """Test that save_review_state creates the JSON file."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            state = _make_review_state()
            save_review_state(state)

            expected_path = tmp_path / "pull-request-review" / "prompts" / "25365" / "review-state.json"
            assert expected_path.exists()

    def test_file_is_valid_json(self, tmp_path):
        """Test that the saved file is valid JSON."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            state = _make_review_state()
            save_review_state(state)

            expected_path = tmp_path / "pull-request-review" / "prompts" / "25365" / "review-state.json"
            content = expected_path.read_text(encoding="utf-8")
            data = json.loads(content)
            assert data["prId"] == 25365

    def test_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created if they don't exist."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            state = _make_review_state(pr_id=99999)
            save_review_state(state)

            expected_path = tmp_path / "pull-request-review" / "prompts" / "99999" / "review-state.json"
            assert expected_path.exists()

    def test_overwrites_existing_file(self, tmp_path):
        """Test that saving again overwrites the existing file."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            state = _make_review_state()
            save_review_state(state)

            # Modify and save again
            state.latestIterationId = 99
            save_review_state(state)

            expected_path = tmp_path / "pull-request-review" / "prompts" / "25365" / "review-state.json"
            data = json.loads(expected_path.read_text(encoding="utf-8"))
            assert data["latestIterationId"] == 99

    def test_saved_data_is_deserializable(self, tmp_path):
        """Test that saved data can be read back correctly by ReviewState.from_dict."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            state = _make_review_state()
            save_review_state(state)

            expected_path = tmp_path / "pull-request-review" / "prompts" / "25365" / "review-state.json"
            data = json.loads(expected_path.read_text(encoding="utf-8"))
            restored = ReviewState.from_dict(data)
            assert restored.prId == 25365
            assert restored.repoName == "dfly-platform-management"

    def test_commit_hash_serialized_when_set(self, tmp_path):
        """Test that commitHash is included in the serialized JSON."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            state = _make_review_state()
            state.commitHash = "abc1234def567890"
            save_review_state(state)

            expected_path = tmp_path / "pull-request-review" / "prompts" / "25365" / "review-state.json"
            data = json.loads(expected_path.read_text(encoding="utf-8"))
            assert data["commitHash"] == "abc1234def567890"

    def test_commit_hash_none_serialized_as_null(self, tmp_path):
        """Test that commitHash is serialized as null when None."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            state = _make_review_state()
            assert state.commitHash is None
            save_review_state(state)

            expected_path = tmp_path / "pull-request-review" / "prompts" / "25365" / "review-state.json"
            data = json.loads(expected_path.read_text(encoding="utf-8"))
            assert data["commitHash"] is None

    def test_new_fields_serialized(self, tmp_path):
        """Test that new fields (modelId, activityLogThreadId, sessions) are serialized."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            state = _make_review_state()
            state.modelId = "claude-4"
            state.activityLogThreadId = 999
            save_review_state(state)

            expected_path = tmp_path / "pull-request-review" / "prompts" / "25365" / "review-state.json"
            data = json.loads(expected_path.read_text(encoding="utf-8"))
            assert data["modelId"] == "claude-4"
            assert data["activityLogThreadId"] == 999
            assert data["sessions"] == []

    def test_narrative_summary_serialized(self, tmp_path):
        """Test that narrativeSummary on OverallSummary is serialized."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            state = _make_review_state()
            state.overallSummary.narrativeSummary = "Great PR"
            save_review_state(state)

            expected_path = tmp_path / "pull-request-review" / "prompts" / "25365" / "review-state.json"
            data = json.loads(expected_path.read_text(encoding="utf-8"))
            assert data["overallSummary"]["narrativeSummary"] == "Great PR"
