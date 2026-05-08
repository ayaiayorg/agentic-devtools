"""Tests for generate_required_setup_script."""

from agentic_devtools.cli.setup.script_generators.required_setup import generate_required_setup_script


class TestGenerateRequiredSetup:
    """Tests for generate_required_setup_script."""

    def test_output_is_string(self):
        """Returns a non-empty string."""
        script = generate_required_setup_script()
        assert isinstance(script, str)
        assert len(script) > 0

    def test_has_shebang(self):
        """Script starts with a shebang line."""
        script = generate_required_setup_script()
        assert script.startswith("#!/usr/bin/env python3")

    def test_contains_corruption_detection(self):
        """Script contains corruption detection logic."""
        script = generate_required_setup_script()
        assert "_detect_corrupted_artifacts" in script

    def test_contains_cleanup(self):
        """Script contains cleanup logic."""
        script = generate_required_setup_script()
        assert "_cleanup_artifacts" in script

    def test_contains_install(self):
        """Script contains install logic."""
        script = generate_required_setup_script()
        assert "pip" in script
        assert "install" in script

    def test_contains_git_hooks(self):
        """Script contains git hooks setup."""
        script = generate_required_setup_script()
        assert "core.hooksPath" in script

    def test_contains_foreground_flag(self):
        """Script supports --foreground flag."""
        script = generate_required_setup_script()
        assert "--foreground" in script

    def test_stdlib_only(self):
        """Script does not import agentic_devtools."""
        script = generate_required_setup_script()
        assert "import agentic_devtools" not in script
        assert "from agentic_devtools" not in script
