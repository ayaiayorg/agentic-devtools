"""Integration test for full agdt-setup flow with mocked filesystem."""

from agentic_devtools.cli.setup.script_generators.constants import (
    COMPLETE_SETUP_FILENAME,
    CONFIGURED_SETUP_FILENAME,
    ORCHESTRATOR_MARKER,
    REPO_SPECIFIC_FILENAME,
    REQUIRED_SETUP_FILENAME,
    ROOT_ENTRY_POINT_FILENAME,
)


class TestFullFlowIntegration:
    """Integration test for full script generation flow."""

    def test_generate_all_scripts(self, tmp_path):
        """All managed scripts are generated in correct locations."""
        from agentic_devtools.cli.setup.commands import _generate_setup_scripts

        # Create a minimal .gitignore
        gi = tmp_path / ".gitignore"
        gi.write_text(".agdt/\n", encoding="utf-8")

        _generate_setup_scripts(tmp_path)

        agdt_dir = tmp_path / ".agdt"
        assert (agdt_dir / REQUIRED_SETUP_FILENAME).exists()
        assert (agdt_dir / CONFIGURED_SETUP_FILENAME).exists()
        assert (agdt_dir / COMPLETE_SETUP_FILENAME).exists()
        assert (tmp_path / ROOT_ENTRY_POINT_FILENAME).exists()
        assert (tmp_path / REPO_SPECIFIC_FILENAME).exists()

    def test_root_entry_point_has_marker(self, tmp_path):
        """Root entry point contains the orchestrator marker."""
        from agentic_devtools.cli.setup.commands import _generate_setup_scripts

        (tmp_path / ".gitignore").write_text(".agdt/\n", encoding="utf-8")
        _generate_setup_scripts(tmp_path)

        content = (tmp_path / ROOT_ENTRY_POINT_FILENAME).read_text(encoding="utf-8")
        assert ORCHESTRATOR_MARKER in content

    def test_repo_specific_not_overwritten(self, tmp_path):
        """Repo-specific script is not overwritten if it already exists."""
        from agentic_devtools.cli.setup.commands import _generate_setup_scripts

        (tmp_path / ".gitignore").write_text(".agdt/\n", encoding="utf-8")

        repo_specific = tmp_path / REPO_SPECIFIC_FILENAME
        repo_specific.write_text("# my custom setup\n", encoding="utf-8")

        _generate_setup_scripts(tmp_path)

        content = repo_specific.read_text(encoding="utf-8")
        assert "# my custom setup" in content

    def test_gitignore_updated(self, tmp_path):
        """Gitignore is updated to track managed scripts."""
        from agentic_devtools.cli.setup.commands import _generate_setup_scripts

        gi = tmp_path / ".gitignore"
        gi.write_text(".agdt/\n", encoding="utf-8")

        _generate_setup_scripts(tmp_path)

        content = gi.read_text(encoding="utf-8")
        assert ".agdt/*" in content
        assert "!.agdt/agentic-devtools-*.py" in content

    def test_idempotent(self, tmp_path):
        """Running twice produces the same result."""
        from agentic_devtools.cli.setup.commands import _generate_setup_scripts

        (tmp_path / ".gitignore").write_text(".agdt/\n", encoding="utf-8")

        _generate_setup_scripts(tmp_path)
        first_content = (tmp_path / ROOT_ENTRY_POINT_FILENAME).read_text(encoding="utf-8")

        _generate_setup_scripts(tmp_path)
        second_content = (tmp_path / ROOT_ENTRY_POINT_FILENAME).read_text(encoding="utf-8")

        assert first_content == second_content

    def test_legacy_migration_on_first_run(self, tmp_path):
        """Legacy setup-dev-tools.py is migrated to repo-specific."""
        from agentic_devtools.cli.setup.commands import _generate_setup_scripts

        (tmp_path / ".gitignore").write_text(".agdt/\n", encoding="utf-8")

        # Create a legacy script (no marker)
        legacy = tmp_path / ROOT_ENTRY_POINT_FILENAME
        legacy.write_text("print('old setup')\n", encoding="utf-8")

        _generate_setup_scripts(tmp_path)

        # Legacy content should be in repo-specific
        repo_specific = tmp_path / REPO_SPECIFIC_FILENAME
        assert repo_specific.exists()
        content = repo_specific.read_text(encoding="utf-8")
        assert "print('old setup')" in content

    def test_migration_failure_skips_root_entry_overwrite(self, tmp_path, capsys):
        """Root entry point is NOT overwritten when legacy migration fails."""
        from unittest.mock import patch

        from agentic_devtools.cli.setup.commands import _generate_setup_scripts

        (tmp_path / ".gitignore").write_text(".agdt/\n", encoding="utf-8")

        # Create a legacy script (no marker) so migration is attempted
        legacy = tmp_path / ROOT_ENTRY_POINT_FILENAME
        legacy.write_text("print('old setup')\n", encoding="utf-8")

        # Make migrate_legacy_content return failure
        with patch(
            "agentic_devtools.cli.setup.script_generators.legacy_migration.migrate_legacy_content",
            return_value=(False, "  ⚠ Failed to read legacy script: fake error"),
        ):
            _generate_setup_scripts(tmp_path)

        out = capsys.readouterr().out
        assert "Skipping" in out
        assert "migration failure" in out
        # Root entry point should still contain the legacy content (NOT overwritten)
        content = legacy.read_text(encoding="utf-8")
        assert "print('old setup')" in content
        assert ORCHESTRATOR_MARKER not in content
