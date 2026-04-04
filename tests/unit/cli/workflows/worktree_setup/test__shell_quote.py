"""Tests for _shell_quote."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import _shell_quote


class TestShellQuote:
    """Tests for the _shell_quote cross-platform quoting helper."""

    def test_unix_uses_shlex_quote(self):
        """On non-Windows platforms, shlex.quote is used."""
        with patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Linux"):
            assert _shell_quote("hello world") == "'hello world'"

    def test_unix_single_quotes_special_chars(self):
        """shlex.quote wraps strings with special characters in single quotes."""
        with patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Linux"):
            assert _shell_quote("it's a test") == """'it'"'"'s a test'"""

    def test_windows_wraps_in_double_quotes(self):
        """On Windows, strings are wrapped in double quotes."""
        with patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Windows"):
            assert _shell_quote("hello world") == '"hello world"'

    def test_windows_escapes_inner_double_quotes(self):
        """On Windows, inner double quotes are doubled."""
        with patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Windows"):
            assert _shell_quote('say "hello"') == '"say ""hello"""'

    def test_windows_escapes_percent(self):
        """On Windows, percent signs are doubled to prevent env var expansion."""
        with patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Windows"):
            assert _shell_quote("100%done") == '"100%%done"'

    def test_windows_escapes_both_quotes_and_percent(self):
        """On Windows, both double quotes and percent signs are escaped."""
        with patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Windows"):
            assert _shell_quote('"100%"') == '"""100%%"""'

    def test_simple_string_no_special_chars(self):
        """A simple string with no special characters is quoted on both platforms."""
        with patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Windows"):
            result_win = _shell_quote("simple")
        with patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Linux"):
            result_unix = _shell_quote("simple")
        assert result_win == '"simple"'
        assert result_unix == "simple"
