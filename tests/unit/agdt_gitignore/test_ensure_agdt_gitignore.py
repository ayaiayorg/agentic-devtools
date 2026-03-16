"""Tests for agentic_devtools.agdt_gitignore.ensure_agdt_gitignore."""

from unittest.mock import patch

from agentic_devtools.agdt_gitignore import (
    AGDT_GITIGNORE_ENTRIES,
    AGDT_GITIGNORE_HEADER,
    ensure_agdt_gitignore,
)


class TestEnsureAgdtGitignore:
    """Tests for ensure_agdt_gitignore function."""

    def test_creates_gitignore(self, tmp_path):
        """Given a valid git_root temp dir, verify file is created with correct content."""
        assert ensure_agdt_gitignore(tmp_path) is True

        gi_path = tmp_path / ".agdt" / ".gitignore"
        assert gi_path.exists()
        content = gi_path.read_text(encoding="utf-8")
        assert content.startswith(AGDT_GITIGNORE_HEADER)
        for entry in AGDT_GITIGNORE_ENTRIES:
            assert entry in content

    def test_overwrites_existing(self, tmp_path):
        """Given an existing .agdt/.gitignore with different content, verify overwrite."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        gi_path = agdt_dir / ".gitignore"
        gi_path.write_text("old content\n", encoding="utf-8")

        assert ensure_agdt_gitignore(tmp_path) is True
        content = gi_path.read_text(encoding="utf-8")
        assert "old content" not in content
        assert AGDT_GITIGNORE_HEADER in content

    def test_returns_false_when_no_git_root(self):
        """ensure_agdt_gitignore(None) returns False."""
        assert ensure_agdt_gitignore(None) is False

    def test_creates_agdt_dir_if_missing(self, tmp_path):
        """Given a git_root without .agdt/, verify dir is created."""
        assert not (tmp_path / ".agdt").exists()
        assert ensure_agdt_gitignore(tmp_path) is True
        assert (tmp_path / ".agdt" / ".gitignore").exists()

    def test_returns_false_on_write_error(self, tmp_path):
        """Mock write_text to raise OSError, verify returns False."""
        with patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
            assert ensure_agdt_gitignore(tmp_path) is False

    def test_entries_constant_values(self):
        """Verify AGDT_GITIGNORE_ENTRIES contains expected values."""
        assert "runtime-bootstrap.json" in AGDT_GITIGNORE_ENTRIES
        assert "workflows/" in AGDT_GITIGNORE_ENTRIES

    def test_content_has_trailing_newline(self, tmp_path):
        """File content ends with a newline."""
        ensure_agdt_gitignore(tmp_path)
        content = (tmp_path / ".agdt" / ".gitignore").read_text(encoding="utf-8")
        assert content.endswith("\n")
