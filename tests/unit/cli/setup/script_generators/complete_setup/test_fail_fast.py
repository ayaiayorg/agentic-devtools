"""Tests for fail-fast chain behaviour."""

from agentic_devtools.cli.setup.script_generators.complete_setup import generate_complete_setup_script
from agentic_devtools.cli.setup.script_generators.root_entry_point import generate_root_entry_point


class TestFailFast:
    """Fail-fast semantics in orchestrator scripts."""

    def test_complete_setup_checks_required_returncode(self):
        """complete-setup checks required-setup exit code."""
        script = generate_complete_setup_script()
        assert "returncode != 0" in script
        assert "sys.exit" in script

    def test_complete_setup_skips_configured_on_failure(self):
        """complete-setup mentions skipping configured on failure."""
        script = generate_complete_setup_script()
        assert "skipping configured" in script.lower()

    def test_root_checks_complete_returncode(self):
        """root entry point checks complete-setup exit code."""
        script = generate_root_entry_point()
        assert "returncode != 0" in script

    def test_root_skips_repo_specific_on_failure(self):
        """root entry point mentions skipping repo-specific on failure."""
        script = generate_root_entry_point()
        assert "skipping repo-specific" in script.lower()
