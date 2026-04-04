"""Tests for _write_pending_auto_start_marker."""

import json

from agentic_devtools.cli.workflows.worktree_setup import (
    _PENDING_AUTO_START_FILENAME,
    _write_pending_auto_start_marker,
)


class TestWritePendingAutoStartMarker:
    """Tests for the _write_pending_auto_start_marker helper."""

    def test_writes_marker_file_with_all_fields(self, tmp_path):
        """Marker file contains all expected fields."""
        _write_pending_auto_start_marker(str(tmp_path), run_id="run-1", start_prompt="hello", model="gpt-4")
        marker_path = tmp_path / ".vscode" / _PENDING_AUTO_START_FILENAME
        assert marker_path.is_file()
        data = json.loads(marker_path.read_text(encoding="utf-8"))
        assert data["run_id"] == "run-1"
        assert data["start_prompt"] == "hello"
        assert data["model"] == "gpt-4"
        assert data["worktree_path"] == str(tmp_path)
        assert "created_utc" in data
        assert data["task_label"] == "agdt-copilot-auto-start"

    def test_writes_marker_with_model_none(self, tmp_path):
        """When model is None, the marker file stores null for model."""
        _write_pending_auto_start_marker(str(tmp_path), run_id="run-2", start_prompt="prompt")
        marker_path = tmp_path / ".vscode" / _PENDING_AUTO_START_FILENAME
        data = json.loads(marker_path.read_text(encoding="utf-8"))
        assert data["model"] is None

    def test_creates_vscode_directory_if_missing(self, tmp_path):
        """The .vscode directory is created when it does not exist."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        _write_pending_auto_start_marker(str(worktree), run_id="run-3", start_prompt="p")
        assert (worktree / ".vscode" / _PENDING_AUTO_START_FILENAME).is_file()

    def test_overwrites_existing_marker(self, tmp_path):
        """Writing a new marker overwrites the previous one."""
        _write_pending_auto_start_marker(str(tmp_path), run_id="old", start_prompt="old-prompt")
        _write_pending_auto_start_marker(str(tmp_path), run_id="new", start_prompt="new-prompt")
        marker_path = tmp_path / ".vscode" / _PENDING_AUTO_START_FILENAME
        data = json.loads(marker_path.read_text(encoding="utf-8"))
        assert data["run_id"] == "new"
        assert data["start_prompt"] == "new-prompt"

    def test_handles_write_error_gracefully(self, tmp_path, capsys):
        """OSError during write is caught and printed to stderr."""
        # Create a file at .vscode so makedirs for the child file fails
        vscode_path = tmp_path / ".vscode"
        vscode_path.mkdir()
        marker_path = vscode_path / _PENDING_AUTO_START_FILENAME
        marker_path.mkdir()  # Make it a directory so open() fails

        _write_pending_auto_start_marker(str(tmp_path), run_id="run-err", start_prompt="p")
        captured = capsys.readouterr()
        assert "failed to write pending auto-start marker" in captured.err

    def test_created_utc_is_iso_format(self, tmp_path):
        """The created_utc field is a valid ISO-8601 timestamp."""
        from datetime import datetime

        _write_pending_auto_start_marker(str(tmp_path), run_id="run-utc", start_prompt="p")
        marker_path = tmp_path / ".vscode" / _PENDING_AUTO_START_FILENAME
        data = json.loads(marker_path.read_text(encoding="utf-8"))
        # Should not raise
        dt = datetime.fromisoformat(data["created_utc"])
        assert dt.tzinfo is not None  # UTC-aware

    def test_preserves_existing_vscode_files(self, tmp_path):
        """Writing marker does not disturb other files in .vscode/."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        settings_file = vscode_dir / "settings.json"
        settings_file.write_text('{"editor.fontSize": 14}', encoding="utf-8")

        _write_pending_auto_start_marker(str(tmp_path), run_id="run-x", start_prompt="p")

        assert settings_file.read_text(encoding="utf-8") == '{"editor.fontSize": 14}'
        assert (vscode_dir / _PENDING_AUTO_START_FILENAME).is_file()
