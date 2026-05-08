"""Tests for generate_root_entry_point."""

from agentic_devtools.cli.setup.script_generators.constants import (
    COMPLETE_SETUP_FILENAME,
    ORCHESTRATOR_MARKER,
    REPO_SPECIFIC_FILENAME,
)
from agentic_devtools.cli.setup.script_generators.root_entry_point import generate_root_entry_point


class TestGenerateRootEntryPoint:
    """Tests for generate_root_entry_point."""

    def test_contains_marker(self):
        """Script contains the AGDT-MANAGED-ORCHESTRATOR marker."""
        script = generate_root_entry_point()
        assert ORCHESTRATOR_MARKER in script

    def test_references_complete_setup(self):
        """Script references the complete-setup filename."""
        script = generate_root_entry_point()
        assert COMPLETE_SETUP_FILENAME in script

    def test_references_repo_specific(self):
        """Script references the repo-specific filename."""
        script = generate_root_entry_point()
        assert REPO_SPECIFIC_FILENAME in script

    def test_fail_fast(self):
        """Script exits on failure."""
        script = generate_root_entry_point()
        assert "returncode != 0" in script
        assert "sys.exit" in script

    def test_skips_repo_specific_on_failure(self):
        """Script mentions skipping repo-specific on failure."""
        script = generate_root_entry_point()
        assert "skipping repo-specific" in script.lower()

    def test_missing_agdt_dir_error(self):
        """Script detects missing .agdt/ directory."""
        script = generate_root_entry_point()
        assert ".agdt/" in script
        assert "agdt-setup" in script
        assert "agdt_dir.is_dir()" in script

    def test_stdlib_only(self):
        """Script does not import agentic_devtools."""
        script = generate_root_entry_point()
        assert "import agentic_devtools" not in script

    def test_foreground_flag(self):
        """Script supports --foreground flag."""
        script = generate_root_entry_point()
        assert "--foreground" in script
        assert 'action="store_true"' in script

    def test_foreground_propagated_to_subprocess(self):
        """Script propagates --foreground to subprocess calls."""
        script = generate_root_entry_point()
        assert "foreground_args" in script

    def test_subprocess_uses_cwd(self):
        """subprocess.run calls use cwd=str(repo_root) for location independence."""
        script = generate_root_entry_point()
        assert "cwd=str(repo_root)" in script

    def test_uses_pathlib(self):
        """Script uses pathlib.Path for cross-platform paths."""
        script = generate_root_entry_point()
        assert "from pathlib import Path" in script
