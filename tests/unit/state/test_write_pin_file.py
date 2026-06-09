"""Tests for agentic_devtools.state.write_pin_file."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_devtools.state import (
    PIN_FILENAME,
    write_pin_file,
)


class TestWritePinFile:
    """Tests for write_pin_file function."""

    def test_writes_pin_file_atomically(self, tmp_path):
        """Pin file is written with correct content."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-123"
        state_dir.mkdir(parents=True)

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            result = write_pin_file(state_dir, workflow="pull-request-review")

        assert result == agdt_dir / PIN_FILENAME
        assert result.exists()

        data = json.loads(result.read_text(encoding="utf-8"))
        assert data["state_dir"] == str(state_dir.resolve())
        assert data["workflow"] == "pull-request-review"
        assert "created_utc" in data
        assert data["ttl_hours"] == 24

    def test_resolves_relative_path_to_absolute(self, tmp_path, monkeypatch):
        """Relative state_dir is resolved to an absolute path."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-123"
        state_dir.mkdir(parents=True)

        monkeypatch.chdir(tmp_path)
        rel_state_dir = Path(".agdt") / "workflows" / "user" / "PROJ-123"

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            result = write_pin_file(rel_state_dir, workflow="pull-request-review")

        data = json.loads(result.read_text(encoding="utf-8"))
        written_path = Path(data["state_dir"])
        assert written_path.is_absolute()
        assert written_path == state_dir.resolve()

    def test_custom_ttl(self, tmp_path):
        """Custom ttl_hours is written."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-123"
        state_dir.mkdir(parents=True)

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            write_pin_file(state_dir, workflow="pull-request-review", ttl_hours=48)

        data = json.loads((agdt_dir / PIN_FILENAME).read_text(encoding="utf-8"))
        assert data["ttl_hours"] == 48

    def test_returns_none_when_not_in_git_repo(self):
        """Returns None when not in a git repo."""
        with patch("agentic_devtools.state._get_git_repo_root", return_value=None):
            result = write_pin_file("/some/path", workflow="pull-request-review")
        assert result is None

    def test_overwrites_existing_pin_file(self, tmp_path):
        """Second write atomically overwrites the first (last writer wins)."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        state_dir_1 = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-111"
        state_dir_1.mkdir(parents=True)
        state_dir_2 = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-222"
        state_dir_2.mkdir(parents=True)

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            write_pin_file(state_dir_1, workflow="pull-request-review")
            write_pin_file(state_dir_2, workflow="pull-request-review")

        data = json.loads((agdt_dir / PIN_FILENAME).read_text(encoding="utf-8"))
        assert data["state_dir"] == str(state_dir_2.resolve())

    def test_cleans_up_temp_file_on_exception(self, tmp_path):
        """Cleans up the temporary file if os.replace fails."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-123"
        state_dir.mkdir(parents=True)

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            with patch("os.replace", side_effect=Exception("mock replace error")):
                with pytest.raises(Exception, match="mock replace error"):
                    write_pin_file(state_dir, workflow="pull-request-review")

        # tmp file should be cleaned up
        assert not any(f.suffix == ".tmp" for f in agdt_dir.iterdir() if f.is_file())

    def test_ignores_oserror_during_cleanup(self, tmp_path):
        """Ignores OSError during cleanup if os.replace fails."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-123"
        state_dir.mkdir(parents=True)

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            with patch("os.replace", side_effect=Exception("mock replace error")):
                with patch("os.unlink", side_effect=OSError("mock unlink error")):
                    with pytest.raises(Exception, match="mock replace error"):
                        write_pin_file(state_dir, workflow="pull-request-review")

    def test_rejects_unrecognized_workflow(self, tmp_path):
        """Raises ValueError for unrecognized workflow names."""
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-123"
        state_dir.mkdir(parents=True)

        with pytest.raises(ValueError, match="workflow must be one of"):
            write_pin_file(state_dir, workflow="unknown-workflow")

    def test_rejects_non_positive_ttl_hours(self, tmp_path):
        """Raises ValueError for non-positive ttl_hours."""
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-123"
        state_dir.mkdir(parents=True)

        with pytest.raises(ValueError, match="ttl_hours must be a positive integer"):
            write_pin_file(state_dir, workflow="pull-request-review", ttl_hours=0)

        with pytest.raises(ValueError, match="ttl_hours must be a positive integer"):
            write_pin_file(state_dir, workflow="pull-request-review", ttl_hours=-1)

    def test_rejects_non_int_ttl_hours(self, tmp_path):
        """Raises ValueError for non-integer ttl_hours."""
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-123"
        state_dir.mkdir(parents=True)

        with pytest.raises(ValueError, match="ttl_hours must be a positive integer"):
            write_pin_file(state_dir, workflow="pull-request-review", ttl_hours=True)

    def test_target_git_root_writes_to_specified_directory(self, tmp_path):
        """When target_git_root is provided and exists, pin is written there."""
        target_root = tmp_path / "target-worktree"
        target_root.mkdir()
        (target_root / ".git").write_text("gitdir: /tmp/worktrees/target-worktree", encoding="utf-8")
        state_dir = target_root / ".agdt" / "workflows" / "ama" / "PROJ-123"
        state_dir.mkdir(parents=True)

        result = write_pin_file(state_dir, workflow="pull-request-review", target_git_root=target_root)

        assert result == target_root / ".agdt" / PIN_FILENAME
        assert result.exists()
        data = json.loads(result.read_text(encoding="utf-8"))
        assert data["state_dir"] == str(state_dir.resolve())

    def test_target_git_root_none_uses_auto_detect(self, tmp_path):
        """When target_git_root is None, falls back to _get_git_repo_root."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-123"
        state_dir.mkdir(parents=True)

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            result = write_pin_file(state_dir, workflow="pull-request-review", target_git_root=None)

        assert result == agdt_dir / PIN_FILENAME

    def test_target_git_root_nonexistent_falls_back_to_auto_detect(self, tmp_path):
        """When target_git_root doesn't exist, falls back to _get_git_repo_root."""
        nonexistent = tmp_path / "does-not-exist"
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-123"
        state_dir.mkdir(parents=True)

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
            result = write_pin_file(state_dir, workflow="pull-request-review", target_git_root=nonexistent)

        assert result == agdt_dir / PIN_FILENAME

    def test_target_git_root_without_git_metadata_falls_back_to_auto_detect(self, tmp_path):
        """Existing directories without .git fall back to _get_git_repo_root."""
        target_root = tmp_path / "not-a-worktree"
        target_root.mkdir()
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-123"
        state_dir.mkdir(parents=True)

        with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path) as mock_get_git_root:
            result = write_pin_file(state_dir, workflow="pull-request-review", target_git_root=target_root)

        mock_get_git_root.assert_called_once()
        assert result == agdt_dir / PIN_FILENAME

    def test_all_recognized_workflows_accepted(self, tmp_path):
        """All 9 recognized workflow names are accepted without error."""
        from agentic_devtools.state import RECOGNIZED_PIN_WORKFLOWS

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        state_dir = tmp_path / ".agdt" / "workflows" / "user" / "PROJ-123"
        state_dir.mkdir(parents=True)

        for wf in RECOGNIZED_PIN_WORKFLOWS:
            with patch("agentic_devtools.state._get_git_repo_root", return_value=tmp_path):
                result = write_pin_file(state_dir, workflow=wf)
            assert result is not None
