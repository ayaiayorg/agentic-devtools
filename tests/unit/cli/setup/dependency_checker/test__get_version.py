"""Tests for _get_version (dependency_checker)."""

from unittest.mock import patch

from agentic_devtools.cli.setup import dependency_checker
from agentic_devtools.cli.setup.dependency_checker import _get_version


class TestGetVersion:
    """Tests for _get_version."""

    def test_git_parses_standard_output(self):
        """Strips 'git version ' prefix from git --version output."""
        with patch.object(dependency_checker, "_run_version", return_value="git version 2.43.0"):
            result = _get_version("git", "/usr/bin/git")
        assert result == "2.43.0"

    def test_git_returns_raw_when_not_standard_format(self):
        """Returns raw output when git output doesn't start with 'git version '."""
        with patch.object(dependency_checker, "_run_version", return_value="2.43.0"):
            result = _get_version("git", "/usr/bin/git")
        assert result == "2.43.0"

    def test_git_returns_none_when_run_version_returns_none(self):
        """Returns None when _run_version returns None for git."""
        with patch.object(dependency_checker, "_run_version", return_value=None):
            result = _get_version("git", "/usr/bin/git")
        assert result is None

    def test_gh_parses_version_keyword(self):
        """Extracts version after 'version' keyword for gh."""
        with patch.object(dependency_checker, "_run_version", return_value="gh version 2.65.0 (2025-01-01)"):
            result = _get_version("gh", "/usr/bin/gh")
        assert result == "2.65.0"

    def test_copilot_parses_version_keyword(self):
        """Extracts version after 'version' keyword for copilot."""
        with patch.object(dependency_checker, "_run_version", return_value="copilot version 1.0.0"):
            result = _get_version("copilot", "/usr/bin/copilot")
        assert result == "1.0.0"

    def test_gh_fallback_to_first_version_token(self):
        """Falls back to first version-like token when no 'version' keyword."""
        with patch.object(dependency_checker, "_run_version", return_value="v2.65.0 release"):
            result = _get_version("gh", "/usr/bin/gh")
        assert result == "v2.65.0"

    def test_gh_fallback_to_digit_first_token(self):
        """Falls back to first token starting with a digit when no keyword."""
        with patch.object(dependency_checker, "_run_version", return_value="2.65.0"):
            result = _get_version("gh", "/usr/bin/gh")
        assert result == "2.65.0"

    def test_gh_returns_raw_when_no_version_token(self):
        """Returns raw string when no version-like token is found for gh."""
        with patch.object(dependency_checker, "_run_version", return_value="no-version-here"):
            result = _get_version("gh", "/usr/bin/gh")
        assert result == "no-version-here"

    def test_gh_returns_none_when_run_version_none(self):
        """Returns None when _run_version returns None for gh."""
        with patch.object(dependency_checker, "_run_version", return_value=None):
            result = _get_version("gh", "/usr/bin/gh")
        assert result is None

    def test_az_parses_version_number(self):
        """Extracts version number from az --version output."""
        with patch.object(dependency_checker, "_run_version", return_value="azure-cli  2.57.0"):
            result = _get_version("az", "/usr/bin/az")
        assert result == "2.57.0"

    def test_az_returns_none_when_no_version_in_output(self):
        """Returns raw string when az output has no version number."""
        with patch.object(dependency_checker, "_run_version", return_value="azure-cli"):
            result = _get_version("az", "/usr/bin/az")
        assert result == "azure-cli"

    def test_az_returns_none_when_run_version_none(self):
        """Returns None when _run_version returns None for az."""
        with patch.object(dependency_checker, "_run_version", return_value=None):
            result = _get_version("az", "/usr/bin/az")
        assert result is None

    def test_code_delegates_to_run_version(self):
        """Returns direct _run_version result for code."""
        with patch.object(dependency_checker, "_run_version", return_value="1.96.0") as mock_rv:
            result = _get_version("code", "/usr/bin/code")
        assert result == "1.96.0"
        mock_rv.assert_called_once_with(["/usr/bin/code", "--version"])

    def test_unknown_tool_delegates_to_run_version(self):
        """Returns direct _run_version result for unknown tool names."""
        with patch.object(dependency_checker, "_run_version", return_value="9.9.9") as mock_rv:
            result = _get_version("unknown-tool", "/usr/bin/unknown-tool")
        assert result == "9.9.9"
        mock_rv.assert_called_once_with(["/usr/bin/unknown-tool", "--version"])
