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
