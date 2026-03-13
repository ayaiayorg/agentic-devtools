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
        "commitHash": "abc1234def567890",
    }


class TestLoadReviewState:
    """Tests for load_review_state function."""

    def test_loads_valid_state(self, tmp_path):
        """Test that a valid JSON file is loaded and deserialized correctly."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            pr_id = 25365
            state_dir = tmp_path / "reviews"
            state_dir.mkdir(parents=True)
            state_file = state_dir / "review-state.json"
            state_file.write_text(json.dumps(_minimal_state_data(pr_id)), encoding="utf-8")

            result = load_review_state(pr_id, fallback_to_branch=False)

        assert isinstance(result, ReviewState)
        assert result.prId == pr_id
        assert result.repoName == "dfly-platform-management"

    def test_raises_file_not_found_when_missing(self, tmp_path):
        """Test that FileNotFoundError is raised when file doesn't exist."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            with pytest.raises(FileNotFoundError, match="25365"):
                load_review_state(25365, fallback_to_branch=False)

    def test_loads_state_with_files_and_folders(self, tmp_path):
        """Test loading a state file that includes files and folders."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            pr_id = 100
            data = _minimal_state_data(pr_id)
            data["folders"] = {"src": {"files": ["/src/app.py"]}}
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

            state_dir = tmp_path / "reviews"
            state_dir.mkdir(parents=True)
            (state_dir / "review-state.json").write_text(json.dumps(data), encoding="utf-8")

            result = load_review_state(pr_id, fallback_to_branch=False)

        assert "src" in result.folders
        assert "/src/app.py" in result.files

    def test_error_message_includes_pr_id(self, tmp_path):
        """Test that the FileNotFoundError message includes the PR ID."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            with pytest.raises(FileNotFoundError) as exc_info:
                load_review_state(99999, fallback_to_branch=False)
        assert "99999" in str(exc_info.value)

    def test_loads_state_with_commit_hash(self, tmp_path):
        """Test that commitHash field is loaded when present in the state file."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            pr_id = 42
            data = _minimal_state_data(pr_id)
            data["commitHash"] = "deadbeef12345678"

            state_dir = tmp_path / "reviews"
            state_dir.mkdir(parents=True)
            (state_dir / "review-state.json").write_text(json.dumps(data), encoding="utf-8")

            result = load_review_state(pr_id, fallback_to_branch=False)

        assert result.commitHash == "deadbeef12345678"

    def test_migration_deletes_old_format_without_commit_hash(self, tmp_path):
        """Test that old-format state without commitHash is deleted and raises FileNotFoundError."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            pr_id = 43
            data = _minimal_state_data(pr_id)
            del data["commitHash"]  # Simulate old format

            state_dir = tmp_path / "reviews"
            state_dir.mkdir(parents=True)
            state_file = state_dir / "review-state.json"
            state_file.write_text(json.dumps(data), encoding="utf-8")

            with pytest.raises(FileNotFoundError, match="43"):
                load_review_state(pr_id, fallback_to_branch=False)

            # File should be deleted
            assert not state_file.exists()

    def test_migration_deletes_old_format_with_folder_thread_id(self, tmp_path):
        """Test that old-format state with FolderEntry threadId is deleted."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            pr_id = 44
            data = _minimal_state_data(pr_id)
            # Has commitHash but also has old-style folder with threadId
            data["folders"] = {"src": {"threadId": 100, "commentId": 200, "status": "unreviewed", "files": []}}

            state_dir = tmp_path / "reviews"
            state_dir.mkdir(parents=True)
            state_file = state_dir / "review-state.json"
            state_file.write_text(json.dumps(data), encoding="utf-8")

            with pytest.raises(FileNotFoundError, match="44"):
                load_review_state(pr_id, fallback_to_branch=False)

            assert not state_file.exists()

    def test_migration_allows_folder_with_zero_thread_id(self, tmp_path):
        """Test that folder data with threadId=0 (legacy but not active) is not flagged."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            pr_id = 45
            data = _minimal_state_data(pr_id)
            data["folders"] = {"src": {"threadId": 0, "commentId": 0, "files": ["/src/app.py"]}}

            state_dir = tmp_path / "reviews"
            state_dir.mkdir(parents=True)
            (state_dir / "review-state.json").write_text(json.dumps(data), encoding="utf-8")

            result = load_review_state(pr_id, fallback_to_branch=False)

        assert "src" in result.folders

    def test_loads_new_fields(self, tmp_path):
        """Test that new fields (modelId, activityLogThreadId, sessions) are loaded."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            pr_id = 46
            data = _minimal_state_data(pr_id)
            data["modelId"] = "claude-4"
            data["activityLogThreadId"] = 999
            data["sessions"] = [
                {
                    "sessionId": "sess-1",
                    "modelId": "claude-4",
                    "startedUtc": "2026-03-01T10:00:00Z",
                    "status": "completed",
                }
            ]

            state_dir = tmp_path / "reviews"
            state_dir.mkdir(parents=True)
            (state_dir / "review-state.json").write_text(json.dumps(data), encoding="utf-8")

            result = load_review_state(pr_id, fallback_to_branch=False)

        assert result.modelId == "claude-4"
        assert result.activityLogThreadId == 999
        assert len(result.sessions) == 1
        assert result.sessions[0].sessionId == "sess-1"

    def test_loads_missing_new_fields_with_defaults(self, tmp_path):
        """Test that missing new fields default correctly."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            pr_id = 47
            data = _minimal_state_data(pr_id)
            # Has commitHash but no modelId, activityLogThreadId, sessions

            state_dir = tmp_path / "reviews"
            state_dir.mkdir(parents=True)
            (state_dir / "review-state.json").write_text(json.dumps(data), encoding="utf-8")

            result = load_review_state(pr_id, fallback_to_branch=False)

        assert result.modelId is None
        assert result.activityLogThreadId == 0
        assert result.sessions == []

    def test_fallback_to_branch_when_local_missing(self, tmp_path):
        """Test branch fallback returns valid ReviewState when local file missing."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            pr_id = 25365
            data = _minimal_state_data(pr_id)
            with patch.object(rs_module, "_load_from_branch", return_value=data) as mock_fb:
                result = load_review_state(pr_id)

        assert isinstance(result, ReviewState)
        assert result.prId == pr_id
        mock_fb.assert_called_once_with(None, None)

    def test_no_fallback_when_disabled(self, tmp_path):
        """Test that fallback_to_branch=False skips branch fallback."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            with patch.object(rs_module, "_load_from_branch") as mock_fb:
                with pytest.raises(FileNotFoundError):
                    load_review_state(25365, fallback_to_branch=False)
            mock_fb.assert_not_called()

    def test_fallback_returns_none_falls_through_to_error(self, tmp_path):
        """Test that FileNotFoundError raised when fallback returns None."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            with patch.object(rs_module, "_load_from_branch", return_value=None):
                with pytest.raises(FileNotFoundError, match="25365"):
                    load_review_state(25365)

    def test_fallback_with_explicit_branch_and_key(self, tmp_path):
        """Test that explicit branch and key are forwarded to _load_from_branch."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            data = _minimal_state_data(25365)
            with patch.object(rs_module, "_load_from_branch", return_value=data) as mock_fb:
                load_review_state(25365, source_branch="feat/X", worktree_key="X-123")
            mock_fb.assert_called_once_with("feat/X", "X-123")

    def test_local_file_takes_precedence_over_branch(self, tmp_path):
        """Test that local file is used even when branch fallback is available."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            pr_id = 25365
            state_dir = tmp_path / "reviews"
            state_dir.mkdir(parents=True)
            state_file = state_dir / "review-state.json"
            state_file.write_text(json.dumps(_minimal_state_data(pr_id)), encoding="utf-8")

            with patch.object(rs_module, "_load_from_branch") as mock_fb:
                result = load_review_state(pr_id)

            assert result.prId == pr_id
            mock_fb.assert_not_called()

    def test_fallback_migration_detection_no_delete(self, tmp_path):
        """Test that branch fallback with incompatible format raises without deleting."""
        with patch.object(rs_module, "get_state_dir", return_value=tmp_path):
            pr_id = 25365
            data = _minimal_state_data(pr_id)
            del data["commitHash"]  # Incompatible format
            with patch.object(rs_module, "_load_from_branch", return_value=data):
                with pytest.raises(FileNotFoundError):
                    load_review_state(pr_id)
            # No local file existed, nothing to delete
            assert not (tmp_path / "reviews" / "review-state.json").exists()
