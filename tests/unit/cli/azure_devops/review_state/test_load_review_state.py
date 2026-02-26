"""Tests for load_review_state function."""

import json
from unittest.mock import patch

import pytest

from agentic_devtools.cli.azure_devops import review_state as rs_module
from agentic_devtools.cli.azure_devops.review_state import ReviewState, load_review_state


def _minimal_state_data(pr_id: int = 25365) -> dict:
    return {
        "prId": pr_id,
        "repoId": "repo-guid",
        "repoName": "dfly-platform-management",
        "project": "DragonflyMgmt",
        "organization": "https://dev.azure.com/swica",
        "latestIterationId": 5,
        "scaffoldedUtc": "2026-02-25T10:00:00Z",
        "overallSummary": {"threadId": 161000, "commentId": 1771800000, "status": "unreviewed"},
        "folders": {},
        "files": {},
    }


class TestLoadReviewState:
    """Tests for load_review_state function."""

    def test_loads_valid_state(self, tmp_path):
        """Test that a valid JSON file is loaded and deserialized correctly."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            pr_id = 25365
            state_dir = tmp_path / "pull-request-review" / "prompts" / str(pr_id)
            state_dir.mkdir(parents=True)
            state_file = state_dir / "review-state.json"
            state_file.write_text(json.dumps(_minimal_state_data(pr_id)), encoding="utf-8")

            result = load_review_state(pr_id)

        assert isinstance(result, ReviewState)
        assert result.prId == pr_id
        assert result.repoName == "dfly-platform-management"

    def test_raises_file_not_found_when_missing(self, tmp_path):
        """Test that FileNotFoundError is raised when file doesn't exist."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            with pytest.raises(FileNotFoundError, match="25365"):
                load_review_state(25365)

    def test_loads_state_with_files_and_folders(self, tmp_path):
        """Test loading a state file that includes files and folders."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            pr_id = 100
            data = _minimal_state_data(pr_id)
            data["folders"] = {"src": {"threadId": 1, "commentId": 2, "status": "unreviewed", "files": ["/src/app.py"]}}
            data["files"] = {
                "/src/app.py": {
                    "threadId": 3,
                    "commentId": 4,
                    "folder": "src",
                    "fileName": "app.py",
                    "status": "unreviewed",
                    "summary": None,
                    "changeTrackingId": None,
                    "suggestions": [],
                }
            }

            state_dir = tmp_path / "pull-request-review" / "prompts" / str(pr_id)
            state_dir.mkdir(parents=True)
            (state_dir / "review-state.json").write_text(json.dumps(data), encoding="utf-8")

            result = load_review_state(pr_id)

        assert "src" in result.folders
        assert "/src/app.py" in result.files

    def test_error_message_includes_pr_id(self, tmp_path):
        """Test that the FileNotFoundError message includes the PR ID."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            with pytest.raises(FileNotFoundError) as exc_info:
                load_review_state(99999)
        assert "99999" in str(exc_info.value)
