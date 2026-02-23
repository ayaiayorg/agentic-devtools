"""Tests for create_agdt_task_issue sync command."""

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


class TestCreateAgdtTaskIssue:
    """Tests for create_agdt_task_issue."""

    def test_requires_title(self, temp_state, mock_gh_cli):
        """Missing issue.title causes sys.exit(1)."""
        state.set_value("issue.description", "What needs doing")
        with pytest.raises(SystemExit):
            issue_commands.create_agdt_task_issue()

    def test_requires_description(self, temp_state, mock_gh_cli):
        """Missing issue.description causes sys.exit(1)."""
        state.set_value("issue.title", "Task title")
        with pytest.raises(SystemExit):
            issue_commands.create_agdt_task_issue()

    def test_dry_run_shows_body(self, temp_state, mock_gh_cli, capsys):
        """Dry run shows description in preview."""
        state.set_value("issue.title", "Task title")
        state.set_value("issue.description", "What needs doing")
        state.set_value("issue.dry_run", True)

        issue_commands.create_agdt_task_issue()

        captured = capsys.readouterr()
        assert "What needs doing" in captured.out

    def test_auto_sets_task_issue_type(self, temp_state, mock_gh_cli):
        """Task issue automatically gets issue type 'Task'."""
        state.set_value("issue.title", "Task title")
        state.set_value("issue.description", "What needs doing")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/ayaiayorg/agentic-devtools/issues/4\n"

        with patch.object(issue_commands, "run_safe", return_value=mock_result) as mock_run:
            issue_commands.create_agdt_task_issue()

        call_args = mock_run.call_args[0][0]
        assert "--type" in call_args
        type_idx = call_args.index("--type")
        assert call_args[type_idx + 1] == "Task"

    def test_acceptance_criteria_appended(self, temp_state, mock_gh_cli, capsys):
        """Acceptance criteria section is appended when provided."""
        state.set_value("issue.title", "Task title")
        state.set_value("issue.description", "What needs doing")
        state.set_value("issue.acceptance_criteria", "- [ ] Tests pass")
        state.set_value("issue.dry_run", True)

        issue_commands.create_agdt_task_issue()

        captured = capsys.readouterr()
        assert "Acceptance Criteria" in captured.out
        assert "Tests pass" in captured.out
