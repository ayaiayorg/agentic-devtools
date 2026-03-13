"""Tests for save_activity_log function."""

import json
from unittest.mock import patch

from agentic_devtools.cli import activity_log as al_module
from agentic_devtools.cli.activity_log import ActivityLog, ActivityLogEntry, save_activity_log


def _make_activity_log() -> ActivityLog:
    return ActivityLog(
        postedCommits={
            "abc1234def567890": ActivityLogEntry(
                postedUtc="2026-03-13T10:00:00Z",
                branchName="feature/DFLY-1234",
                worktreeKey="DFLY-1234",
                prCommentPosted=True,
                jiraCommentPosted=False,
                prId=42,
            ),
        }
    )


class TestSaveActivityLog:
    """Tests for save_activity_log function."""

    def test_creates_file(self, tmp_path):
        """Test that save_activity_log creates the JSON file."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            save_activity_log(_make_activity_log())

            expected_path = tmp_path / "activity-log" / "activity-log.json"
            assert expected_path.exists()

    def test_file_is_valid_json(self, tmp_path):
        """Test that the saved file is valid JSON."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            save_activity_log(_make_activity_log())

            expected_path = tmp_path / "activity-log" / "activity-log.json"
            content = expected_path.read_text(encoding="utf-8")
            data = json.loads(content)
            assert "postedCommits" in data
            assert "abc1234def567890" in data["postedCommits"]

    def test_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created if they don't exist."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            save_activity_log(ActivityLog())

            expected_path = tmp_path / "activity-log" / "activity-log.json"
            assert expected_path.exists()

    def test_overwrites_existing_file(self, tmp_path):
        """Test that saving again overwrites the existing file."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            log = _make_activity_log()
            save_activity_log(log)

            # Add a new entry and save again
            log.mark_as_posted(
                "newcommit123",
                posted_utc="2026-03-14T10:00:00Z",
                branch_name="feature/Y",
                worktree_key="Y",
            )
            save_activity_log(log)

            expected_path = tmp_path / "activity-log" / "activity-log.json"
            data = json.loads(expected_path.read_text(encoding="utf-8"))
            assert len(data["postedCommits"]) == 2

    def test_saved_data_is_deserializable(self, tmp_path):
        """Test that saved data can be read back correctly by ActivityLog.from_dict."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            save_activity_log(_make_activity_log())

            expected_path = tmp_path / "activity-log" / "activity-log.json"
            data = json.loads(expected_path.read_text(encoding="utf-8"))
            restored = ActivityLog.from_dict(data)
            assert "abc1234def567890" in restored.postedCommits
            assert restored.postedCommits["abc1234def567890"].branchName == "feature/DFLY-1234"

    def test_posted_commits_serialized_correctly(self, tmp_path):
        """Test that postedCommits entries are serialized with all fields including prId."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            save_activity_log(_make_activity_log())

            expected_path = tmp_path / "activity-log" / "activity-log.json"
            data = json.loads(expected_path.read_text(encoding="utf-8"))
            entry = data["postedCommits"]["abc1234def567890"]
            assert entry["prId"] == 42
            assert entry["prCommentPosted"] is True
            assert entry["jiraCommentPosted"] is False

    def test_save_calls_mark_dirty(self, tmp_path):
        """Test that save_activity_log calls mark_dirty after writing."""
        from agentic_devtools.cli.git.agdt_branch import _reset_dirty, is_dirty

        _reset_dirty()
        try:
            with patch.object(al_module, "get_state_dir", return_value=tmp_path):
                save_activity_log(_make_activity_log())
                assert is_dirty() is True
        finally:
            _reset_dirty()

    def test_save_succeeds_when_mark_dirty_import_fails(self, tmp_path):
        """Test that save_activity_log still writes the file when mark_dirty import fails."""
        with patch.object(al_module, "get_state_dir", return_value=tmp_path):
            import builtins

            original_import = builtins.__import__

            def failing_import(name, *args, **kwargs):
                if "agdt_branch" in name:
                    raise ImportError("simulated")
                return original_import(name, *args, **kwargs)

            log = _make_activity_log()
            with patch.object(builtins, "__import__", side_effect=failing_import):
                save_activity_log(log)

            expected_path = tmp_path / "activity-log" / "activity-log.json"
            assert expected_path.exists()
            data = json.loads(expected_path.read_text(encoding="utf-8"))
            assert "abc1234def567890" in data["postedCommits"]
