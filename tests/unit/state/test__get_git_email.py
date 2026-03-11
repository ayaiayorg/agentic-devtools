"""Tests for agentic_devtools.state._get_git_email."""

from unittest.mock import MagicMock, patch

from agentic_devtools import state


class TestGetGitEmail:
    """Tests for the _get_git_email helper."""

    def test_returns_email_on_success(self):
        """Returns trimmed email when git config succeeds."""
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "albert.marsnik@example.com\n"
        with patch("agentic_devtools.state.subprocess.run", return_value=mock):
            assert state._get_git_email() == "albert.marsnik@example.com"

    def test_returns_empty_string_on_failure(self):
        """Returns empty string when git config fails."""
        mock = MagicMock()
        mock.returncode = 1
        mock.stdout = ""
        with patch("agentic_devtools.state.subprocess.run", return_value=mock):
            assert state._get_git_email() == ""

    def test_returns_empty_string_on_file_not_found(self):
        """Returns empty string when git is not installed."""
        with patch(
            "agentic_devtools.state.subprocess.run",
            side_effect=FileNotFoundError("git not found"),
        ):
            assert state._get_git_email() == ""

    def test_returns_empty_string_on_os_error(self):
        """Returns empty string on OSError."""
        with patch(
            "agentic_devtools.state.subprocess.run",
            side_effect=OSError("permission denied"),
        ):
            assert state._get_git_email() == ""
