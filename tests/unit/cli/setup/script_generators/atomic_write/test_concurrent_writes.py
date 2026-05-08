"""Tests for atomic_write."""

from agentic_devtools.cli.setup.script_generators.atomic_write import atomic_write


class TestAtomicWrite:
    """Tests for atomic_write."""

    def test_writes_content(self, tmp_path):
        """Writes content to the target path."""
        target = tmp_path / "test.py"
        atomic_write(target, "hello world")
        assert target.read_text(encoding="utf-8") == "hello world"

    def test_creates_parent_dirs(self, tmp_path):
        """Creates parent directories if they don't exist."""
        target = tmp_path / "sub" / "dir" / "test.py"
        atomic_write(target, "content")
        assert target.exists()
        assert target.read_text(encoding="utf-8") == "content"

    def test_overwrites_existing(self, tmp_path):
        """Overwrites existing file content."""
        target = tmp_path / "test.py"
        target.write_text("old", encoding="utf-8")
        atomic_write(target, "new")
        assert target.read_text(encoding="utf-8") == "new"

    def test_no_partial_writes(self, tmp_path):
        """On error, target is not left in a partial state."""
        from unittest.mock import patch

        target = tmp_path / "test.py"
        target.write_text("original", encoding="utf-8")

        # Simulate os.replace raising an error after the temp file is written
        with patch("os.replace", side_effect=OSError("disk full")):
            try:
                atomic_write(target, "new content")
            except OSError:
                pass
        # Original file must remain unchanged
        assert target.read_text(encoding="utf-8") == "original"
