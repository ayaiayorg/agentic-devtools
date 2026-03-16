"""Tests for agentic_devtools.agdt_gitignore.ensure_agdt_gitignore."""

from unittest.mock import patch

from agentic_devtools.agdt_gitignore import (
    AGDT_GITIGNORE_ENTRIES,
    AGDT_GITIGNORE_HEADER,
    ensure_agdt_gitignore,
)


class TestEnsureAgdtGitignore:
    """Tests for the ensure_agdt_gitignore function."""

    def test_creates_gitignore_with_correct_content(self, tmp_path):
        """Given a valid git_root, creates .agdt/.gitignore with header + entries."""
        result = ensure_agdt_gitignore(tmp_path)

        assert result is True
        gitignore_path = tmp_path / ".agdt" / ".gitignore"
        assert gitignore_path.exists()
        content = gitignore_path.read_text(encoding="utf-8")
        assert content.startswith(AGDT_GITIGNORE_HEADER)
        for entry in AGDT_GITIGNORE_ENTRIES:
            assert entry in content

    def test_overwrites_existing_gitignore(self, tmp_path):
        """Overwrites an existing .agdt/.gitignore with different content."""
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir()
        gitignore_path = agdt_dir / ".gitignore"
        gitignore_path.write_text("old content\n", encoding="utf-8")

        result = ensure_agdt_gitignore(tmp_path)

        assert result is True
        content = gitignore_path.read_text(encoding="utf-8")
        assert "old content" not in content
        assert content.startswith(AGDT_GITIGNORE_HEADER)

    def test_returns_false_when_no_git_root(self):
        """Returns False when git_root is None."""
        assert ensure_agdt_gitignore(None) is False

    def test_creates_agdt_dir_if_missing(self, tmp_path):
        """Creates .agdt/ directory if it doesn't exist."""
        assert not (tmp_path / ".agdt").exists()

        result = ensure_agdt_gitignore(tmp_path)

        assert result is True
        assert (tmp_path / ".agdt").is_dir()

    def test_returns_false_on_write_error(self, tmp_path):
        """Returns False when write_text raises OSError."""
        with patch("pathlib.Path.write_text", side_effect=OSError("permission denied")):
            result = ensure_agdt_gitignore(tmp_path)

        assert result is False

    def test_entries_constant_values(self):
        """AGDT_GITIGNORE_ENTRIES contains expected values."""
        assert "runtime-bootstrap.json" in AGDT_GITIGNORE_ENTRIES
        assert "workflows/" in AGDT_GITIGNORE_ENTRIES

    def test_content_ends_with_newline(self, tmp_path):
        """The generated file content ends with a trailing newline."""
        ensure_agdt_gitignore(tmp_path)

        content = (tmp_path / ".agdt" / ".gitignore").read_text(encoding="utf-8")
        assert content.endswith("\n")
