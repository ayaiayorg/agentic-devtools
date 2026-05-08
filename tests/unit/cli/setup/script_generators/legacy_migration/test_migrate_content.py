"""Tests for migrate_legacy_content."""

from agentic_devtools.cli.setup.script_generators.legacy_migration import migrate_legacy_content


class TestMigrateContent:
    """Tests for migrate_legacy_content."""

    def test_moves_to_new_file(self, tmp_path):
        """Legacy content moves to new file when target doesn't exist."""
        legacy = tmp_path / "setup-dev-tools.py"
        legacy.write_text("print('legacy')\n", encoding="utf-8")
        target = tmp_path / "setup-repo-specific-dev-tools.py"

        msg = migrate_legacy_content(legacy, target)
        assert target.exists()
        assert "print('legacy')" in target.read_text(encoding="utf-8")
        assert "moved to" in msg

    def test_appends_when_target_exists(self, tmp_path):
        """Legacy content appended below separator when target exists."""
        legacy = tmp_path / "setup-dev-tools.py"
        legacy.write_text("print('legacy')\n", encoding="utf-8")
        target = tmp_path / "setup-repo-specific-dev-tools.py"
        target.write_text("print('existing')\n", encoding="utf-8")

        msg = migrate_legacy_content(legacy, target)
        content = target.read_text(encoding="utf-8")
        assert "print('existing')" in content
        assert "print('legacy')" in content
        assert "Migrated from legacy" in content
        assert "appended" in msg

    def test_empty_legacy(self, tmp_path):
        """Empty legacy file skips migration."""
        legacy = tmp_path / "setup-dev-tools.py"
        legacy.write_text("", encoding="utf-8")
        target = tmp_path / "setup-repo-specific-dev-tools.py"

        msg = migrate_legacy_content(legacy, target)
        assert "empty" in msg
        assert not target.exists()

    def test_missing_legacy(self, tmp_path):
        """Nonexistent legacy file reports error."""
        legacy = tmp_path / "nonexistent.py"
        target = tmp_path / "target.py"

        msg = migrate_legacy_content(legacy, target)
        assert "Failed to read" in msg
