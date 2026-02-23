"""Tests for create_agdt_bug_issue sync command."""

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


class TestCreateAgdtBugIssue:
    """Tests for create_agdt_bug_issue."""

    def test_requires_title(self, temp_state, mock_gh_cli):
        """Missing issue.title causes sys.exit(1)."""
        state.set_value("issue.steps_to_reproduce", "1. Do thing")
        state.set_value("issue.expected_behavior", "Works")
        state.set_value("issue.actual_behavior", "Fails")
        with pytest.raises(SystemExit):
            issue_commands.create_agdt_bug_issue()

    def test_requires_steps_to_reproduce(self, temp_state, mock_gh_cli):
        """Missing issue.steps_to_reproduce causes sys.exit(1)."""
        state.set_value("issue.title", "Bug title")
        state.set_value("issue.expected_behavior", "Works")
        state.set_value("issue.actual_behavior", "Fails")
        with pytest.raises(SystemExit):
            issue_commands.create_agdt_bug_issue()

    def test_requires_expected_behavior(self, temp_state, mock_gh_cli):
        """Missing issue.expected_behavior causes sys.exit(1)."""
        state.set_value("issue.title", "Bug title")
        state.set_value("issue.steps_to_reproduce", "1. Do thing")
        state.set_value("issue.actual_behavior", "Fails")
        with pytest.raises(SystemExit):
            issue_commands.create_agdt_bug_issue()

    def test_requires_actual_behavior(self, temp_state, mock_gh_cli):
        """Missing issue.actual_behavior causes sys.exit(1)."""
        state.set_value("issue.title", "Bug title")
        state.set_value("issue.steps_to_reproduce", "1. Do thing")
        state.set_value("issue.expected_behavior", "Works")
        with pytest.raises(SystemExit):
            issue_commands.create_agdt_bug_issue()

    def test_dry_run_shows_structured_body(self, temp_state, mock_gh_cli, capsys):
        """Dry run shows structured sections in body."""
        state.set_value("issue.title", "Bug title")
        state.set_value("issue.steps_to_reproduce", "1. Run command")
        state.set_value("issue.expected_behavior", "It works")
        state.set_value("issue.actual_behavior", "It fails")
        state.set_value("issue.dry_run", True)

        with patch.object(issue_commands, "_get_environment_info", return_value="## Environment\n"):
            issue_commands.create_agdt_bug_issue()

        captured = capsys.readouterr()
        assert "Steps to Reproduce" in captured.out
        assert "Expected Behavior" in captured.out
        assert "Actual Behavior" in captured.out

    def test_auto_sets_bug_label(self, temp_state, mock_gh_cli):
        """Bug issue automatically gets 'bug' label."""
        state.set_value("issue.title", "Bug title")
        state.set_value("issue.steps_to_reproduce", "1. Run command")
        state.set_value("issue.expected_behavior", "It works")
        state.set_value("issue.actual_behavior", "It fails")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/ayaiayorg/agentic-devtools/issues/1\n"

        with patch.object(issue_commands, "_get_environment_info", return_value="## Environment\n"):
            with patch.object(issue_commands, "run_safe", return_value=mock_result) as mock_run:
                issue_commands.create_agdt_bug_issue()

        call_args = mock_run.call_args[0][0]
        assert "--label" in call_args
        label_idx = call_args.index("--label")
        assert call_args[label_idx + 1] == "bug"

    def test_includes_workaround_section(self, temp_state, mock_gh_cli, capsys):
        """Workaround section is included when provided."""
        state.set_value("issue.title", "Bug title")
        state.set_value("issue.steps_to_reproduce", "1. Run command")
        state.set_value("issue.expected_behavior", "It works")
        state.set_value("issue.actual_behavior", "It fails")
        state.set_value("issue.workaround", "Use old version")
        state.set_value("issue.dry_run", True)

        with patch.object(issue_commands, "_get_environment_info", return_value="## Environment\n"):
            issue_commands.create_agdt_bug_issue()

        captured = capsys.readouterr()
        assert "Workaround" in captured.out
        assert "Use old version" in captured.out

    def test_includes_error_output_section(self, temp_state, mock_gh_cli, capsys):
        """Error output section is included when provided."""
        state.set_value("issue.title", "Bug title")
        state.set_value("issue.steps_to_reproduce", "1. Run command")
        state.set_value("issue.expected_behavior", "It works")
        state.set_value("issue.actual_behavior", "It fails")
        state.set_value("issue.error_output", "Error: FileNotFoundError")
        state.set_value("issue.dry_run", True)

        with patch.object(issue_commands, "_get_environment_info", return_value="## Environment\n"):
            issue_commands.create_agdt_bug_issue()

        captured = capsys.readouterr()
        assert "Error Output" in captured.out
        assert "FileNotFoundError" in captured.out
