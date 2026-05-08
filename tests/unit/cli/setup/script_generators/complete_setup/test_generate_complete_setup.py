"""Tests for generate_complete_setup_script."""

from agentic_devtools.cli.setup.script_generators.complete_setup import generate_complete_setup_script
from agentic_devtools.cli.setup.script_generators.constants import (
    CONFIGURED_SETUP_FILENAME,
    REQUIRED_SETUP_FILENAME,
)


class TestGenerateCompleteSetup:
    """Tests for generate_complete_setup_script."""

    def test_references_required_setup(self):
        """Script references the required-setup filename."""
        script = generate_complete_setup_script()
        assert REQUIRED_SETUP_FILENAME in script

    def test_references_configured_setup(self):
        """Script references the configured-setup filename."""
        script = generate_complete_setup_script()
        assert CONFIGURED_SETUP_FILENAME in script

    def test_fail_fast_semantics(self):
        """Script checks return code and exits on failure."""
        script = generate_complete_setup_script()
        assert "returncode != 0" in script
        assert "sys.exit" in script

    def test_skips_configured_on_failure(self):
        """Script mentions skipping configured on failure."""
        script = generate_complete_setup_script()
        assert "skipping configured" in script.lower()

    def test_stdlib_only(self):
        """Script does not import agentic_devtools."""
        script = generate_complete_setup_script()
        assert "import agentic_devtools" not in script
        assert "from agentic_devtools" not in script

    def test_foreground_flag(self):
        """Script supports --foreground flag."""
        script = generate_complete_setup_script()
        assert "--foreground" in script

    def test_foreground_always_propagated(self):
        """--foreground is always passed (no conditional branch)."""
        script = generate_complete_setup_script()
        assert 'foreground_args = ["--foreground"]' in script
        assert "if args.foreground" not in script

    def test_uses_pathlib(self):
        """Script uses pathlib.Path for cross-platform paths."""
        script = generate_complete_setup_script()
        assert "from pathlib import Path" in script
