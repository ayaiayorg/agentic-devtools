"""Tests for create_agdt_issue sync command."""

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


class TestCreateAgdtIssue:
    """Tests for create_agdt_issue."""

    def test_requires_title(self, temp_state, mock_gh_cli):
        """Missing issue.title causes sys.exit(1)."""
        state.set_value("issue.description", "Details")
        with pytest.raises(SystemExit):
            issue_commands.create_agdt_issue()

    def test_requires_description(self, temp_state, mock_gh_cli):
        """Missing issue.description causes sys.exit(1)."""
        state.set_value("issue.title", "My issue")
        with pytest.raises(SystemExit):
            issue_commands.create_agdt_issue()

    def test_dry_run_prints_preview(self, temp_state, mock_gh_cli, capsys):
        """Dry run prints preview without calling gh."""
        state.set_value("issue.title", "Test issue")
        state.set_value("issue.description", "Test body")
        state.set_value("issue.dry_run", True)

        issue_commands.create_agdt_issue()

        captured = capsys.readouterr()
        assert "PREVIEW" in captured.out
        assert "Test issue" in captured.out
        assert "Test body" in captured.out

    def test_dry_run_shows_labels(self, temp_state, mock_gh_cli, capsys):
        """Dry run shows labels when set."""
        state.set_value("issue.title", "Test issue")
        state.set_value("issue.description", "Test body")
        state.set_value("issue.labels", "bug,enhancement")
        state.set_value("issue.dry_run", True)

        issue_commands.create_agdt_issue()

        captured = capsys.readouterr()
        assert "bug" in captured.out

    def test_dry_run_shows_issue_type(self, temp_state, mock_gh_cli, capsys):
        """Dry run shows issue type when set."""
        state.set_value("issue.title", "Test issue")
        state.set_value("issue.description", "Test body")
        state.set_value("issue.issue_type", "Bug")
        state.set_value("issue.dry_run", True)

        issue_commands.create_agdt_issue()

        captured = capsys.readouterr()
        assert "Bug" in captured.out

    def test_creates_issue_via_gh(self, temp_state, mock_gh_cli):
        """Successful issue creation via gh CLI."""
        state.set_value("issue.title", "My issue")
        state.set_value("issue.description", "Details")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/ayaiayorg/agentic-devtools/issues/999\n"

        with patch.object(issue_commands, "run_safe", return_value=mock_result) as mock_run:
            issue_commands.create_agdt_issue()

        call_args = mock_run.call_args[0][0]
        assert "gh" in call_args
        assert "issue" in call_args
        assert "create" in call_args
        assert "ayaiayorg/agentic-devtools" in call_args

    def test_gh_call_uses_shell_false(self, temp_state, mock_gh_cli):
        """gh issue create must use shell=False to prevent env-var expansion on Windows."""
        state.set_value("issue.title", "My issue")
        state.set_value("issue.description", "Details")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/ayaiayorg/agentic-devtools/issues/999\n"

        with patch.object(issue_commands, "run_safe", return_value=mock_result) as mock_run:
            issue_commands.create_agdt_issue()

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs.get("shell") is False

    def test_gh_failure_exits(self, temp_state, mock_gh_cli):
        """gh CLI failure causes sys.exit with non-zero code."""
        state.set_value("issue.title", "My issue")
        state.set_value("issue.description", "Details")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "gh: authentication error"

        with patch.object(issue_commands, "run_safe", return_value=mock_result):
            with pytest.raises(SystemExit) as exc_info:
                issue_commands.create_agdt_issue()
        assert exc_info.value.code != 0

    def test_related_issue_appended(self, temp_state, mock_gh_cli):
        """Related issue numbers are appended to body."""
        state.set_value("issue.title", "My issue")
        state.set_value("issue.description", "Details")
        state.set_value("issue.related_issue", "123")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/ayaiayorg/agentic-devtools/issues/999\n"

        with patch.object(issue_commands, "run_safe", return_value=mock_result) as mock_run:
            issue_commands.create_agdt_issue()

        call_args = mock_run.call_args[0][0]
        body_idx = call_args.index("--body") + 1
        assert "Related to #123" in call_args[body_idx]

    def test_saved_to_state(self, temp_state, mock_gh_cli):
        """Created issue URL is saved to state."""
        state.set_value("issue.title", "My issue")
        state.set_value("issue.description", "Details")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/ayaiayorg/agentic-devtools/issues/999\n"

        with patch.object(issue_commands, "run_safe", return_value=mock_result):
            issue_commands.create_agdt_issue()

        url = state.get_value("issue.created_issue_url")
        assert url == "https://github.com/ayaiayorg/agentic-devtools/issues/999"
