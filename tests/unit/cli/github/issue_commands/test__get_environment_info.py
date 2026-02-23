"""Tests for _get_environment_info helper."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.github import issue_commands
from agentic_devtools.cli.github.issue_commands import _get_environment_info


class TestGetEnvironmentInfo:
    """Tests for _get_environment_info."""

    def test_returns_markdown_section(self):
        """Returns a markdown section starting with '## Environment'."""
        with patch.object(issue_commands, "run_safe", side_effect=OSError("not found")):
            result = _get_environment_info()
        assert result.startswith("## Environment")

    def test_includes_os_info(self):
        """Includes OS information."""
        with patch.object(issue_commands, "run_safe", side_effect=OSError("not found")):
            result = _get_environment_info()
        assert "- OS:" in result

    def test_includes_python_version(self):
        """Includes Python version."""
        with patch.object(issue_commands, "run_safe", side_effect=OSError("not found")):
            result = _get_environment_info()
        assert "- Python:" in result

    def test_includes_agdt_version(self):
        """Includes agentic-devtools version."""
        with patch.object(issue_commands, "run_safe", side_effect=OSError("not found")):
            result = _get_environment_info()
        assert "- agentic-devtools:" in result

    def test_handles_missing_vscode(self):
        """Handles VS Code not being installed (OSError)."""
        with patch.object(issue_commands, "run_safe", side_effect=OSError("not found")):
            result = _get_environment_info()
        assert "- VS Code:" in result
        assert "unknown" in result

    def test_includes_git_version(self):
        """Includes Git version when git is available."""
        mock_git_result = MagicMock()
        mock_git_result.returncode = 0
        mock_git_result.stdout = "git version 2.43.0\n"

        call_count = [0]

        def side_effect(args, **kwargs):
            call_count[0] += 1
            if args[0] == "code":
                raise OSError("not found")
            return mock_git_result

        with patch.object(issue_commands, "run_safe", side_effect=side_effect):
            result = _get_environment_info()
        assert "- Git:" in result
        assert "2.43.0" in result
