"""Tests for missing .agdt/ directory error in root entry point."""

from agentic_devtools.cli.setup.script_generators.root_entry_point import generate_root_entry_point


class TestMissingAgdtDir:
    """Tests for missing .agdt/ directory error handling."""

    def test_script_checks_for_agdt_dir(self):
        """Generated script checks if .agdt/ exists."""
        script = generate_root_entry_point()
        assert "agdt_dir" in script or ".agdt" in script

    def test_actionable_error_message(self):
        """Script provides actionable error when .agdt/ is missing."""
        script = generate_root_entry_point()
        assert "agdt-setup" in script
