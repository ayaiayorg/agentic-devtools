"""Tests for migrate_legacy_content."""

from unittest.mock import patch

from agentic_devtools.cli.setup.script_generators.legacy_migration import migrate_legacy_content


class TestMigrateContent:
    """Tests for migrate_legacy_content."""

    def test_moves_to_new_file(self, tmp_path):
        """Legacy content moves to new file when target doesn't exist."""
        legacy = tmp_path / "setup-dev-tools.py"
        legacy.write_text("print('legacy')\n", encoding="utf-8")
        target = tmp_path / "setup-repo-specific-dev-tools.py"

        success, msg = migrate_legacy_content(legacy, target)
        assert success is True
        assert target.exists()
        assert "print('legacy')" in target.read_text(encoding="utf-8")
        assert "moved to" in msg

    def test_appends_when_target_exists(self, tmp_path):
        """Legacy content appended below separator when target exists."""
        legacy = tmp_path / "setup-dev-tools.py"
        legacy.write_text("print('legacy')\n", encoding="utf-8")
        target = tmp_path / "setup-repo-specific-dev-tools.py"
        target.write_text("print('existing')\n", encoding="utf-8")

        success, msg = migrate_legacy_content(legacy, target)
        assert success is True
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

        success, msg = migrate_legacy_content(legacy, target)
        assert success is True
        assert "empty" in msg
        assert not target.exists()

    def test_missing_legacy(self, tmp_path):
        """Nonexistent legacy file reports error."""
        legacy = tmp_path / "nonexistent.py"
        target = tmp_path / "target.py"

        success, msg = migrate_legacy_content(legacy, target)
        assert success is False
        assert "Failed to read" in msg

    def test_uses_atomic_write(self, tmp_path):
        """migrate_legacy_content uses atomic_write for safe file writes."""
        legacy = tmp_path / "setup-dev-tools.py"
        legacy.write_text("print('legacy')\n", encoding="utf-8")
        target = tmp_path / "setup-repo-specific-dev-tools.py"

        with patch("agentic_devtools.cli.setup.script_generators.legacy_migration.atomic_write") as mock_aw:
            success, msg = migrate_legacy_content(legacy, target)
            assert success is True
            mock_aw.assert_called_once_with(target, "print('legacy')\n")

    def test_write_failure(self, tmp_path):
        """Reports error when atomic_write raises OSError."""
        legacy = tmp_path / "setup-dev-tools.py"
        legacy.write_text("print('legacy')\n", encoding="utf-8")
        target = tmp_path / "setup-repo-specific-dev-tools.py"

        with patch(
            "agentic_devtools.cli.setup.script_generators.legacy_migration.atomic_write",
            side_effect=OSError("disk full"),
        ):
            success, msg = migrate_legacy_content(legacy, target)
            assert success is False
            assert "Failed to migrate" in msg

    def test_target_unicode_decode_error(self, tmp_path):
        """Reports error when existing target file has invalid encoding."""
        legacy = tmp_path / "setup-dev-tools.py"
        legacy.write_text("print('legacy')\n", encoding="utf-8")
        target = tmp_path / "setup-repo-specific-dev-tools.py"
        # Write invalid UTF-8 bytes to the target file
        target.write_bytes(b"\x80\x81\x82\x83")

        success, msg = migrate_legacy_content(legacy, target)
        assert success is False
        assert "Failed to read" in msg
