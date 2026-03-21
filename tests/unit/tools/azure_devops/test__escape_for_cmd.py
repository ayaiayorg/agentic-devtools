"""Tests for agentic_devtools.tools.azure_devops._escape_for_cmd."""

from unittest.mock import patch

from agentic_devtools.tools.azure_devops import _escape_for_cmd


class TestEscapeForCmd:
    """Tests for the _escape_for_cmd helper function."""

    @patch("agentic_devtools.tools.azure_devops.sys")
    def test_doubles_percent_on_windows(self, mock_sys):
        mock_sys.platform = "win32"
        assert _escape_for_cmd("feat(%ISSUE%): title") == "feat(%%ISSUE%%): title"

    @patch("agentic_devtools.tools.azure_devops.sys")
    def test_noop_on_non_windows(self, mock_sys):
        mock_sys.platform = "linux"
        assert _escape_for_cmd("feat(%ISSUE%): title") == "feat(%ISSUE%): title"

    @patch("agentic_devtools.tools.azure_devops.sys")
    def test_no_percent_unchanged_on_windows(self, mock_sys):
        mock_sys.platform = "win32"
        assert _escape_for_cmd("normal text") == "normal text"

    @patch("agentic_devtools.tools.azure_devops.sys")
    def test_empty_string(self, mock_sys):
        mock_sys.platform = "win32"
        assert _escape_for_cmd("") == ""

    @patch("agentic_devtools.tools.azure_devops.sys")
    def test_multiple_percent_patterns(self, mock_sys):
        mock_sys.platform = "win32"
        assert _escape_for_cmd("%A% and %B%") == "%%A%% and %%B%%"
