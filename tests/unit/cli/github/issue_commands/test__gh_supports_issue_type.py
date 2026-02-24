"""Tests for _gh_supports_issue_type helper."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.github import issue_commands
from agentic_devtools.cli.github.issue_commands import _gh_supports_issue_type


class TestGhSupportsIssueType:
    """Tests for _gh_supports_issue_type."""

    def test_returns_true_when_type_in_stdout(self):
        """Returns True when '--type' appears in gh help stdout."""
        mock_result = MagicMock()
        mock_result.stdout = "Flags:\n  --type string   Issue type\n"
        mock_result.stderr = ""
        with patch.object(issue_commands, "run_safe", return_value=mock_result):
            assert _gh_supports_issue_type() is True

    def test_returns_true_when_type_in_stderr(self):
        """Returns True when '--type' appears in gh help stderr."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "Flags:\n  --type string   Issue type\n"
        with patch.object(issue_commands, "run_safe", return_value=mock_result):
            assert _gh_supports_issue_type() is True

    def test_returns_false_when_type_not_in_output(self):
        """Returns False when '--type' does not appear in gh help output."""
        mock_result = MagicMock()
        mock_result.stdout = "Flags:\n  --title string   Issue title\n"
        mock_result.stderr = ""
        with patch.object(issue_commands, "run_safe", return_value=mock_result):
            assert _gh_supports_issue_type() is False

    def test_returns_false_on_oserror(self):
        """Returns False when gh CLI raises OSError (not found)."""
        with patch.object(issue_commands, "run_safe", side_effect=OSError("not found")):
            assert _gh_supports_issue_type() is False
