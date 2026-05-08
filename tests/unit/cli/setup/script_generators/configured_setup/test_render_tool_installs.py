"""Tests for render_tool_installs."""

from agentic_devtools.cli.setup.script_generators.configured_setup import render_tool_installs


class TestRenderToolInstalls:
    """Tests for render_tool_installs."""

    def test_known_tool(self):
        """Known tool generates install snippet."""
        result = render_tool_installs(["ruff"])
        assert "pip install ruff" in result
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

    def test_empty_list(self):
        """Empty list produces empty output."""
        result = render_tool_installs([])
        assert result == ""
