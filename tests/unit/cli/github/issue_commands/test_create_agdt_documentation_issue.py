"""Tests for create_agdt_documentation_issue sync command."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.github import issue_commands


@pytest.fixture
def temp_state(tmp_path):
    """Create a temporary state directory."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        state.clear_state()
        yield tmp_path


@pytest.fixture
def mock_gh_cli():
    """Mock the gh CLI check to always pass."""
    with patch.object(issue_commands, "_check_gh_cli"):
        yield


class TestCreateAgdtDocumentationIssue:
    """Tests for create_agdt_documentation_issue."""

    def test_requires_title(self, temp_state, mock_gh_cli):
        """Missing issue.title causes sys.exit(1)."""
        state.set_value("issue.whats_missing", "Docs are missing")
        with pytest.raises(SystemExit):
            issue_commands.create_agdt_documentation_issue()

    def test_requires_whats_missing(self, temp_state, mock_gh_cli):
        """Missing issue.whats_missing causes sys.exit(1)."""
        state.set_value("issue.title", "Documentation issue")
        with pytest.raises(SystemExit):
            issue_commands.create_agdt_documentation_issue()

    def test_dry_run_shows_structured_body(self, temp_state, mock_gh_cli, capsys):
        """Dry run shows structured documentation sections."""
        state.set_value("issue.title", "Documentation issue")
        state.set_value("issue.whats_missing", "The README is outdated")
        state.set_value("issue.dry_run", True)

        issue_commands.create_agdt_documentation_issue()

        captured = capsys.readouterr()
        assert "Missing" in captured.out
        assert "outdated" in captured.out

    def test_auto_sets_documentation_label(self, temp_state, mock_gh_cli):
        """Documentation issue automatically gets 'documentation' label."""
        state.set_value("issue.title", "Documentation issue")
        state.set_value("issue.whats_missing", "The README is outdated")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/ayaiayorg/agentic-devtools/issues/3\n"

        with patch.object(issue_commands, "run_safe", return_value=mock_result) as mock_run:
            issue_commands.create_agdt_documentation_issue()

        call_args = mock_run.call_args[0][0]
        assert "--label" in call_args
        label_idx = call_args.index("--label")
        assert call_args[label_idx + 1] == "documentation"

    def test_optional_sections_included(self, temp_state, mock_gh_cli, capsys):
        """Optional sections appear when provided."""
        state.set_value("issue.title", "Documentation issue")
        state.set_value("issue.whats_missing", "Missing docs")
        state.set_value("issue.suggested_content", "Add this section")
        state.set_value("issue.affected_commands", "agdt-create-agdt-issue")
        state.set_value("issue.dry_run", True)

        issue_commands.create_agdt_documentation_issue()

        captured = capsys.readouterr()
        assert "Suggested Content" in captured.out
        assert "Affected Commands" in captured.out
