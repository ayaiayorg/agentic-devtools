"""Tests for create_agdt_feature_issue sync command."""

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


class TestCreateAgdtFeatureIssue:
    """Tests for create_agdt_feature_issue."""

    def test_requires_title(self, temp_state, mock_gh_cli):
        """Missing issue.title causes sys.exit(1)."""
        state.set_value("issue.motivation", "Need it")
        state.set_value("issue.proposed_solution", "Do this")
        with pytest.raises(SystemExit):
            issue_commands.create_agdt_feature_issue()

    def test_requires_motivation(self, temp_state, mock_gh_cli):
        """Missing issue.motivation causes sys.exit(1)."""
        state.set_value("issue.title", "Feature title")
        state.set_value("issue.proposed_solution", "Do this")
        with pytest.raises(SystemExit):
            issue_commands.create_agdt_feature_issue()

    def test_requires_proposed_solution(self, temp_state, mock_gh_cli):
        """Missing issue.proposed_solution causes sys.exit(1)."""
        state.set_value("issue.title", "Feature title")
        state.set_value("issue.motivation", "Need it")
        with pytest.raises(SystemExit):
            issue_commands.create_agdt_feature_issue()

    def test_dry_run_shows_structured_body(self, temp_state, mock_gh_cli, capsys):
        """Dry run shows Motivation and Proposed Solution sections."""
        state.set_value("issue.title", "Feature title")
        state.set_value("issue.motivation", "Need this for workflow")
        state.set_value("issue.proposed_solution", "Add new command")
        state.set_value("issue.dry_run", True)

        issue_commands.create_agdt_feature_issue()

        captured = capsys.readouterr()
        assert "Motivation" in captured.out
        assert "Proposed Solution" in captured.out

    def test_auto_sets_enhancement_label(self, temp_state, mock_gh_cli):
        """Feature issue automatically gets 'enhancement' label."""
        state.set_value("issue.title", "Feature title")
        state.set_value("issue.motivation", "Need it")
        state.set_value("issue.proposed_solution", "Do this")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/ayaiayorg/agentic-devtools/issues/2\n"

        with patch.object(issue_commands, "run_safe", return_value=mock_result) as mock_run:
            issue_commands.create_agdt_feature_issue()

        call_args = mock_run.call_args[0][0]
        assert "--label" in call_args
        label_idx = call_args.index("--label")
        assert call_args[label_idx + 1] == "enhancement"

    def test_optional_sections_included(self, temp_state, mock_gh_cli, capsys):
        """Optional sections appear when provided."""
        state.set_value("issue.title", "Feature title")
        state.set_value("issue.motivation", "Need it")
        state.set_value("issue.proposed_solution", "Do this")
        state.set_value("issue.alternatives_considered", "Could also do X")
        state.set_value("issue.breaking_changes", "None")
        state.set_value("issue.examples", "agdt-new-cmd --flag")
        state.set_value("issue.dry_run", True)

        issue_commands.create_agdt_feature_issue()

        captured = capsys.readouterr()
        assert "Alternatives Considered" in captured.out
        assert "Breaking Changes" in captured.out
        assert "Examples" in captured.out
