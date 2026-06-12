"""Tests for agentic_devtools.cli.azure_devops.commands._escape_for_cmd."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.commands import _escape_for_cmd


class TestEscapeForCmd:
    """Tests for the _escape_for_cmd helper function."""

    @patch("agentic_devtools.cli.azure_devops.commands.sys.platform", "win32")
    def test_doubles_percent_on_windows(self) -> None:
        assert _escape_for_cmd("has%ISSUE%") == "has%%ISSUE%%"

    @patch("agentic_devtools.cli.azure_devops.commands.sys.platform", "linux")
    def test_noop_on_non_windows(self) -> None:
        assert _escape_for_cmd("a&b|c%d") == "a&b|c%d"

    @patch("agentic_devtools.cli.azure_devops.commands.sys.platform", "win32")
    def test_no_special_chars_unchanged_on_windows(self) -> None:
        assert _escape_for_cmd("normal/branch-name") == "normal/branch-name"

    @patch("agentic_devtools.cli.azure_devops.commands.sys.platform", "win32")
    def test_empty_string_on_windows(self) -> None:
        assert _escape_for_cmd("") == ""

    @patch("agentic_devtools.cli.azure_devops.commands.sys.platform", "win32")
    def test_escapes_ampersand_with_caret_on_windows(self) -> None:
        assert _escape_for_cmd("branch&name") == "branch^&name"

    @patch("agentic_devtools.cli.azure_devops.commands.sys.platform", "win32")
    def test_escapes_pipe_with_caret_on_windows(self) -> None:
        assert _escape_for_cmd("branch|name") == "branch^|name"

    @patch("agentic_devtools.cli.azure_devops.commands.sys.platform", "win32")
    def test_escapes_less_than_with_caret_on_windows(self) -> None:
        assert _escape_for_cmd("branch<name") == "branch^<name"

    @patch("agentic_devtools.cli.azure_devops.commands.sys.platform", "win32")
    def test_escapes_greater_than_with_caret_on_windows(self) -> None:
        assert _escape_for_cmd("branch>name") == "branch^>name"

    @patch("agentic_devtools.cli.azure_devops.commands.sys.platform", "win32")
    def test_escapes_caret_by_doubling_on_windows(self) -> None:
        assert _escape_for_cmd("branch^name") == "branch^^name"

    @patch("agentic_devtools.cli.azure_devops.commands.sys.platform", "win32")
    def test_percent_doubled_and_metachar_escaped_together(self) -> None:
        """When value has both % and a metachar, both escaping rules are applied."""
        assert _escape_for_cmd("has%and&both") == "has%%and^&both"

    @patch("agentic_devtools.cli.azure_devops.commands.sys.platform", "win32")
    def test_embedded_double_quote_and_metachar_use_caret_escaping(self) -> None:
        assert _escape_for_cmd('branch"name&test') == 'branch^"name^&test'
