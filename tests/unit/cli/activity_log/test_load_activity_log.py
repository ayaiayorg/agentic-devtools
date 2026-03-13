"""Tests for load_activity_log function."""

import json
from unittest.mock import patch

from agentic_devtools.cli import activity_log as al_module
from agentic_devtools.cli.activity_log import ActivityLog, load_activity_log


def _minimal_log_data() -> dict:
    return {
        "postedCommits": {
            "abc123": {
                "postedUtc": "2026-03-13T10:00:00Z",
                "branchName": "feature/X",
                "worktreeKey": "X",
                "prCommentPosted": True,
                "jiraCommentPosted": False,
                "prId": 42,
            }
        }
    }


class TestLoadActivityLog:
    """Tests for load_activity_log function."""

    def test_loads_valid_local_file(self, tmp_path):
        """Test that a valid local JSON file is loaded and deserialized correctly."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            log_dir = tmp_path / "activity-log"
            log_dir.mkdir(parents=True)
            log_file = log_dir / "activity-log.json"
            log_file.write_text(json.dumps(_minimal_log_data()), encoding="utf-8")

            result = load_activity_log(fallback_to_branch=False)

        assert isinstance(result, ActivityLog)
        assert "abc123" in result.postedCommits
        assert result.postedCommits["abc123"].prId == 42

    def test_returns_empty_when_no_local_file_no_fallback(self, tmp_path):
        """Test returns empty ActivityLog when no local file and fallback disabled."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            result = load_activity_log(fallback_to_branch=False)

        assert isinstance(result, ActivityLog)
        assert result.postedCommits == {}

    def test_returns_empty_when_no_local_file_fallback_enabled(self, tmp_path):
        """Test returns empty ActivityLog when no local file and branch has nothing."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            with patch.object(al_module, "_load_from_branch", return_value=None):
                result = load_activity_log()

        assert isinstance(result, ActivityLog)
        assert result.postedCommits == {}

    def test_branch_fallback_loads_from_artifacts(self, tmp_path):
        """Test branch fallback: loads from load_workflow_artifacts when local file missing."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            with patch.object(al_module, "_load_from_branch", return_value=_minimal_log_data()) as mock_fb:
                result = load_activity_log()

        assert isinstance(result, ActivityLog)
        assert "abc123" in result.postedCommits
        mock_fb.assert_called_once_with(None, None)

    def test_branch_fallback_returns_empty_when_none(self, tmp_path):
        """Test branch fallback returns empty when _load_from_branch returns None."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            with patch.object(al_module, "_load_from_branch", return_value=None):
                result = load_activity_log()

        assert result.postedCommits == {}

    def test_branch_fallback_returns_empty_on_exception(self, tmp_path):
        """Test branch fallback returns empty when _load_from_branch raises exception."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            with patch.object(al_module, "_load_from_branch", side_effect=RuntimeError("boom")):
                result = load_activity_log()

        assert isinstance(result, ActivityLog)
        assert result.postedCommits == {}

    def test_source_branch_forwarded(self, tmp_path):
        """Test that source_branch is forwarded to _load_from_branch."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            with patch.object(al_module, "_load_from_branch", return_value=None) as mock_fb:
                load_activity_log(source_branch="feat/X")

        mock_fb.assert_called_once_with("feat/X", None)

    def test_worktree_key_forwarded(self, tmp_path):
        """Test that worktree_key is forwarded to _load_from_branch."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            with patch.object(al_module, "_load_from_branch", return_value=None) as mock_fb:
                load_activity_log(worktree_key="KEY-123")

        mock_fb.assert_called_once_with(None, "KEY-123")

    def test_explicit_branch_and_key_forwarded(self, tmp_path):
        """Test that explicit branch and key are forwarded to _load_from_branch."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            with patch.object(al_module, "_load_from_branch", return_value=None) as mock_fb:
                load_activity_log(source_branch="feat/Y", worktree_key="Y-456")

        mock_fb.assert_called_once_with("feat/Y", "Y-456")

    def test_local_file_takes_precedence_over_branch(self, tmp_path):
        """Test that local file is used even when branch fallback is available."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            log_dir = tmp_path / "activity-log"
            log_dir.mkdir(parents=True)
            log_file = log_dir / "activity-log.json"
            log_file.write_text(json.dumps(_minimal_log_data()), encoding="utf-8")

            with patch.object(al_module, "_load_from_branch") as mock_fb:
                result = load_activity_log()

        assert "abc123" in result.postedCommits
        mock_fb.assert_not_called()

    def test_returns_empty_when_source_branch_cannot_be_resolved(self, tmp_path):
        """Test returns empty when source_branch cannot be resolved from state."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            # _load_from_branch returns None when branch can't be resolved
            with patch.object(al_module, "_load_from_branch", return_value=None):
                result = load_activity_log()

        assert result.postedCommits == {}
