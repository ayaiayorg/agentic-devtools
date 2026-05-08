"""Tests for generate_configured_setup_script."""

from agentic_devtools.cli.setup.script_generators.configured_setup import generate_configured_setup_script


class TestGenerateConfiguredSetup:
    """Tests for generate_configured_setup_script."""

    def test_no_tools_selected(self):
        """No tools selected produces informational message."""
        script = generate_configured_setup_script()
        assert "No optional tools configured" in script

    def test_empty_tools_list(self):
        """Empty list produces informational message."""
        script = generate_configured_setup_script([])
        assert "No optional tools configured" in script

    def test_ruff_selected(self):
        """Selecting ruff uses sys.executable for deterministic pip install."""
        script = generate_configured_setup_script(["ruff"])
        assert "sys.executable" in script
        assert "'pip'" in script
        assert "'install'" in script
        assert "'ruff'" in script

    def test_cspell_selected(self):
        """Selecting cspell produces npm install as argv list."""
        script = generate_configured_setup_script(["cspell"])
        assert "'npm'" in script
        assert "'install'" in script
        assert "'-g'" in script
        assert "'cspell'" in script

    def test_unknown_tool_ignored(self):
        """Unknown tool names are silently skipped."""
        script = generate_configured_setup_script(["nonexistent_tool"])
        assert "nonexistent_tool" not in script
        assert "No optional tools configured" in script

    def test_stdlib_only(self):
        """Script does not import agentic_devtools."""
        script = generate_configured_setup_script(["ruff"])
        assert "import agentic_devtools" not in script
        assert "from agentic_devtools" not in script

    def test_idempotent(self):
        """Same input produces identical output."""
        a = generate_configured_setup_script(["ruff", "cspell"])
        b = generate_configured_setup_script(["ruff", "cspell"])
        assert a == b
