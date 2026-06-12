"""Tests for agentic_devtools.cli.pr_template.ensure_pr_body_template."""

from pathlib import Path
from unittest.mock import patch

from agentic_devtools.cli.pr_template import TEMPLATE_RELATIVE_PATH, ensure_pr_body_template


class TestEnsurePrBodyTemplate:
    """Tests for ensure_pr_body_template()."""

    def test_creates_template_when_missing(self, tmp_path):
        """Creates default PR body template when it does not exist."""
        result = ensure_pr_body_template(tmp_path)

        assert result is True
        template_path = tmp_path / TEMPLATE_RELATIVE_PATH
        assert template_path.exists()
        content = template_path.read_text(encoding="utf-8")
        assert "{{ fullCommitMessage }}" in content
        assert "Checkliste" in content

    def test_does_not_overwrite_existing(self, tmp_path):
        """Does not overwrite an existing template."""
        template_path = tmp_path / TEMPLATE_RELATIVE_PATH
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text("custom body template", encoding="utf-8")

        result = ensure_pr_body_template(tmp_path)

        assert result is False
        assert template_path.read_text(encoding="utf-8") == "custom body template"

    def test_creates_parent_directories(self, tmp_path):
        """Creates parent directories if they don't exist."""
        result = ensure_pr_body_template(tmp_path)

        assert result is True
        template_path = tmp_path / TEMPLATE_RELATIVE_PATH
        assert template_path.parent.is_dir()

    def test_removes_legacy_md_template_and_creates_j2(self, tmp_path):
        """Removes legacy .md template and creates the .j2 template in its place."""
        legacy_path = tmp_path / ".agdt/config/pull-request-template.md"
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.write_text("old md content", encoding="utf-8")

        result = ensure_pr_body_template(tmp_path)

        assert result is True
        assert not legacy_path.exists()
        template_path = tmp_path / TEMPLATE_RELATIVE_PATH
        assert template_path.exists()

    def test_skips_backup_write_when_backup_already_exists(self, tmp_path):
        """Does not overwrite an existing backup when migrating the legacy .md template."""
        legacy_path = tmp_path / ".agdt/config/pull-request-template.md"
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.write_text("old md content", encoding="utf-8")
        backup_path = tmp_path / ".agdt/config/pull-request-template.md.bak"
        backup_path.write_text("existing backup", encoding="utf-8")

        result = ensure_pr_body_template(tmp_path)

        assert result is True
        assert not legacy_path.exists()
        # Existing backup must not be overwritten
        assert backup_path.read_text(encoding="utf-8") == "existing backup"

    def test_warns_when_legacy_unlink_fails(self, tmp_path, capsys):
        """Prints a warning to stderr when the legacy .md file cannot be deleted."""
        legacy_path = tmp_path / ".agdt/config/pull-request-template.md"
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.write_text("old md content", encoding="utf-8")

        original_unlink = Path.unlink

        def failing_unlink(self, missing_ok=False):
            if self == legacy_path:
                raise OSError("permission denied")
            original_unlink(self, missing_ok=missing_ok)

        with patch.object(Path, "unlink", failing_unlink):
            result = ensure_pr_body_template(tmp_path)

        assert result is True
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "permission denied" in captured.err
        template_path = tmp_path / TEMPLATE_RELATIVE_PATH
        assert template_path.exists()
