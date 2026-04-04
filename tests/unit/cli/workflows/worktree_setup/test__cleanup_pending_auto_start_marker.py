"""Tests for _cleanup_pending_auto_start_marker."""

from agentic_devtools.cli.workflows.worktree_setup import (
    _PENDING_AUTO_START_FILENAME,
    _cleanup_pending_auto_start_marker,
)


class TestCleanupPendingAutoStartMarker:
    """Tests for the _cleanup_pending_auto_start_marker helper."""

    def test_removes_existing_marker_file(self, tmp_path):
        """Marker file is deleted when it exists."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        marker = vscode_dir / _PENDING_AUTO_START_FILENAME
        marker.write_text("{}", encoding="utf-8")

        _cleanup_pending_auto_start_marker(str(tmp_path))

        assert not marker.exists()

    def test_no_error_when_marker_does_not_exist(self, tmp_path):
        """No error is raised when the marker file is absent."""
        _cleanup_pending_auto_start_marker(str(tmp_path))
        # Should not raise

    def test_no_error_when_vscode_dir_does_not_exist(self, tmp_path):
        """No error when .vscode/ directory does not exist."""
        worktree = tmp_path / "no-vscode"
        worktree.mkdir()
        _cleanup_pending_auto_start_marker(str(worktree))
        # Should not raise

    def test_handles_removal_error_gracefully(self, tmp_path, capsys):
        """OSError during removal is caught and printed to stderr."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        marker = vscode_dir / _PENDING_AUTO_START_FILENAME
        # Make marker a non-empty directory so os.remove() fails
        marker.mkdir()
        (marker / "child.txt").write_text("x", encoding="utf-8")

        _cleanup_pending_auto_start_marker(str(tmp_path))
        captured = capsys.readouterr()
        assert "failed to remove pending auto-start marker" in captured.err

    def test_preserves_other_vscode_files(self, tmp_path):
        """Other files in .vscode/ are not affected by cleanup."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        marker = vscode_dir / _PENDING_AUTO_START_FILENAME
        marker.write_text("{}", encoding="utf-8")
        settings = vscode_dir / "settings.json"
        settings.write_text("{}", encoding="utf-8")

        _cleanup_pending_auto_start_marker(str(tmp_path))

        assert not marker.exists()
        assert settings.exists()
