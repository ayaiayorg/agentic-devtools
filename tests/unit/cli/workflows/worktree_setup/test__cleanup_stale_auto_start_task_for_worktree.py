"""Tests for _cleanup_stale_auto_start_task_for_worktree."""

import json
from unittest.mock import patch

import agentic_devtools.cli.workflows.worktree_setup as _ws_module
from agentic_devtools.cli.workflows.worktree_setup import (
    _AUTO_START_TASK_LABEL,
    _cleanup_stale_auto_start_task_for_worktree,
)


class TestCleanupStaleAutoStartTaskForWorktree:
    """Tests for the _cleanup_stale_auto_start_task_for_worktree helper."""

    def test_removes_stale_task_from_tasks_json(self, tmp_path):
        """Should remove the auto-start task when tasks.json exists."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        tasks_data = {
            "version": "2.0.0",
            "tasks": [
                {
                    "label": _AUTO_START_TASK_LABEL,
                    "type": "shell",
                    "command": "echo stale",
                    "runOptions": {"runOn": "folderOpen"},
                },
                {
                    "label": "other-task",
                    "type": "shell",
                    "command": "echo keep",
                },
            ],
        }
        tasks_path.write_text(json.dumps(tasks_data), encoding="utf-8")

        _cleanup_stale_auto_start_task_for_worktree(str(tmp_path))

        result = json.loads(tasks_path.read_text(encoding="utf-8"))
        labels = [t["label"] for t in result["tasks"]]
        assert _AUTO_START_TASK_LABEL not in labels
        assert "other-task" in labels

    def test_no_op_when_tasks_json_missing(self, tmp_path):
        """Should not raise when .vscode/tasks.json does not exist."""
        _cleanup_stale_auto_start_task_for_worktree(str(tmp_path))

    def test_no_op_when_vscode_dir_missing(self, tmp_path):
        """Should not raise when .vscode directory does not exist."""
        nonexistent = str(tmp_path / "nonexistent_worktree")
        _cleanup_stale_auto_start_task_for_worktree(nonexistent)

    def test_no_op_when_no_matching_task(self, tmp_path):
        """Should leave tasks.json unchanged when no auto-start task present."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        tasks_data = {
            "version": "2.0.0",
            "tasks": [
                {"label": "build", "type": "shell", "command": "make"},
            ],
        }
        tasks_path.write_text(json.dumps(tasks_data), encoding="utf-8")

        _cleanup_stale_auto_start_task_for_worktree(str(tmp_path))

        result = json.loads(tasks_path.read_text(encoding="utf-8"))
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["label"] == "build"

    def test_silently_handles_invalid_json(self, tmp_path):
        """Should not raise when tasks.json contains invalid JSON."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        tasks_path.write_text("not valid json {{{", encoding="utf-8")

        # Should not raise
        _cleanup_stale_auto_start_task_for_worktree(str(tmp_path))

    def test_silently_handles_unexpected_exception(self, tmp_path):
        """Should not raise when an unexpected error occurs (e.g. OS error on isfile)."""
        with patch.object(_ws_module.os.path, "isfile", side_effect=OSError("boom")):
            # Should not raise despite the OSError
            _cleanup_stale_auto_start_task_for_worktree(str(tmp_path))

    def test_delegates_to_remove_stale_auto_start_task(self, tmp_path):
        """Should call _remove_stale_auto_start_task with correct paths."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        tasks_data = {"version": "2.0.0", "tasks": []}
        tasks_path.write_text(json.dumps(tasks_data), encoding="utf-8")

        with patch("agentic_devtools.cli.workflows.worktree_setup._remove_stale_auto_start_task") as mock_remove:
            _cleanup_stale_auto_start_task_for_worktree(str(tmp_path))

        mock_remove.assert_called_once_with(
            str(tasks_path),
            str(vscode_dir),
            _AUTO_START_TASK_LABEL,
        )
