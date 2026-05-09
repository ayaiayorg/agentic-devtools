"""Tests for cleanup_artifacts."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.setup.script_generators.required_setup import cleanup_artifacts


class TestCleanupArtifacts:
    """Tests for cleanup_artifacts."""

    def test_removes_directory(self, tmp_path):
        """Directories are removed via shutil.rmtree."""
        d = tmp_path / "~gentic-devtools"
        d.mkdir()
        (d / "file.py").write_text("x", encoding="utf-8")
        msgs = cleanup_artifacts([d])
        assert not d.exists()
        assert any("Removed" in m for m in msgs)

    def test_removes_file(self, tmp_path):
        """Files are removed via unlink."""
        f = tmp_path / "_editable_impl_agentic_devtools.pth"
        f.write_text("x", encoding="utf-8")
        msgs = cleanup_artifacts([f])
        assert not f.exists()
        assert any("Removed" in m for m in msgs)

    def test_handles_permission_error(self, tmp_path, monkeypatch):
        """Permission errors are reported, not raised."""
        f = tmp_path / "locked.pth"
        f.write_text("x", encoding="utf-8")
        monkeypatch.setattr(Path, "unlink", lambda self, **kw: (_ for _ in ()).throw(PermissionError("denied")))
        msgs = cleanup_artifacts([f])
        assert any("Permission denied" in m for m in msgs)

    def test_empty_list(self):
        """Empty artifact list returns empty messages."""
        assert cleanup_artifacts([]) == []

    def test_rmtree_permission_error(self, tmp_path):
        """Permission errors during rmtree are handled gracefully."""
        sp = tmp_path / "site-packages"
        sp.mkdir()
        d = sp / "~gentic-devtools"
        d.mkdir()
        (d / "file.py").write_text("x", encoding="utf-8")

        def failing_rmtree(path, **kw):
            raise PermissionError("read-only")

        with patch("shutil.rmtree", side_effect=failing_rmtree):
            msgs = cleanup_artifacts([d])
        assert any("Permission denied" in m for m in msgs)

    def test_removes_symlink(self, tmp_path):
        """Symlinks are removed via unlink."""
        link = tmp_path / "link"
        link.write_text("x", encoding="utf-8")
        with patch.object(Path, "is_symlink", return_value=True):
            msgs = cleanup_artifacts([link])
        assert not link.exists()
        assert any("Removed" in m for m in msgs)

    def test_handles_oserror(self, tmp_path):
        """OSError (non-PermissionError) is handled gracefully."""
        f = tmp_path / "broken.pth"
        f.write_text("x", encoding="utf-8")
        with (
            patch.object(Path, "is_symlink", return_value=False),
            patch.object(Path, "is_dir", return_value=False),
            patch.object(Path, "unlink", side_effect=OSError("disk error")),
        ):
            msgs = cleanup_artifacts([f])
        assert any("Failed to remove" in m for m in msgs)
