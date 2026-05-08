"""Tests for render_tool_installs."""

from agentic_devtools.cli.setup.script_generators.configured_setup import render_tool_installs


class TestRenderToolInstalls:
    """Tests for render_tool_installs."""

    def test_known_tool(self):
        """Known pip tool generates install snippet with sys.executable."""
        result = render_tool_installs(["ruff"])
        assert "sys.executable" in result
        assert "'pip'" in result
        assert "'install'" in result
        assert "'ruff'" in result
        assert "Installing ruff" in result

    def test_unknown_tool_skipped(self):
        """Unknown tool produces empty output."""
        result = render_tool_installs(["nonexistent"])
        assert result.strip() == ""

    def test_multiple_tools(self):
        """Multiple tools generate multiple install snippets."""
        result = render_tool_installs(["ruff", "cspell"])
        assert "ruff" in result
        assert "cspell" in result

    def test_npm_tool_uses_shell_on_windows(self):
        """npm-based tools include shell=(sys.platform == "win32")."""
        result = render_tool_installs(["cspell"])
        assert 'shell=(sys.platform == "win32")' in result

    def test_pip_tool_no_shell_flag(self):
        """pip-based tools do not include shell flag."""
        result = render_tool_installs(["ruff"])
        assert "shell=" not in result

    def test_empty_list(self):
        """Empty list produces empty output."""
        result = render_tool_installs([])
        assert result == ""
