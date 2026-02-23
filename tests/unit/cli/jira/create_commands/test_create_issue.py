"""
Tests for Jira CLI commands (create_epic, create_issue, create_subtask, add_comment, get_issue).

These tests validate the command-line interface functions that create and manage Jira issues.
They use mocked API calls to avoid network dependencies.
"""

from unittest.mock import MagicMock, patch

import pytest

from agdt_ai_helpers import state
from agdt_ai_helpers.cli import jira
from agdt_ai_helpers.cli.jira import (
    comment_commands,
    create_commands,
    get_commands,
)


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state.clear_state()
    yield


@pytest.fixture
def mock_jira_env():
    """Set up environment for Jira API calls."""
    with patch.dict("os.environ", {"JIRA_COPILOT_PAT": "test-token"}):
        yield


@pytest.fixture
def mock_requests_module():
    """Mock the requests module for API calls."""
    mock_module = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"key": "DFLY-9999", "id": "12345"}
    mock_response.raise_for_status = MagicMock()
    mock_module.post.return_value = mock_response
    mock_module.get.return_value = mock_response
    # Patch in all implementation modules where _get_requests is imported
    with patch.object(create_commands, "_get_requests", return_value=mock_module):
        with patch.object(comment_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "_get_requests", return_value=mock_module):
                yield mock_module


class TestCreateIssueDryRun:
    """Tests for create_issue command in dry run mode."""

    def test_create_issue_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test create_issue in dry run mode."""
        jira.set_jira_value("summary", "Test Issue")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "functionality")
        jira.set_jira_value("benefit", "value")
        jira.set_jira_value("dry_run", True)

        jira.create_issue()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Test Issue" in captured.out

    def test_create_issue_custom_type(self, temp_state_dir, clear_state_before, capsys):
        """Test create_issue with custom issue type."""
        jira.set_jira_value("summary", "Test Bug")
        jira.set_jira_value("issue_type", "Bug")
        jira.set_jira_value("role", "tester")
        jira.set_jira_value("desired_outcome", "bug fix")
        jira.set_jira_value("benefit", "stability")
        jira.set_jira_value("dry_run", True)

        jira.create_issue()

        captured = capsys.readouterr()
        assert "Bug" in captured.out

    def test_create_issue_missing_summary(self, temp_state_dir, clear_state_before):
        """Test create_issue fails with missing summary."""
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_issue()
        assert exc_info.value.code == 1

    def test_create_issue_missing_role(self, temp_state_dir, clear_state_before):
        """Test create_issue fails with missing role."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_issue()
        assert exc_info.value.code == 1

    def test_create_issue_missing_desired_outcome(self, temp_state_dir, clear_state_before):
        """Test create_issue fails with missing desired_outcome."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("benefit", "value")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_issue()
        assert exc_info.value.code == 1

    def test_create_issue_missing_benefit(self, temp_state_dir, clear_state_before):
        """Test create_issue fails with missing benefit."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "feature")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_issue()
        assert exc_info.value.code == 1


class TestCreateIssueWithMock:
    """Tests for create_issue with mocked API calls."""

    def test_create_issue_success(
        self,
        temp_state_dir,
        clear_state_before,
        mock_jira_env,
        mock_requests_module,
        capsys,
    ):
        """Test successful issue creation."""
        jira.set_jira_value("summary", "Test Issue")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        jira.create_issue()

        captured = capsys.readouterr()
        assert "DFLY-9999" in captured.out
        assert "created successfully" in captured.out

    def test_create_issue_api_error(self, temp_state_dir, clear_state_before, mock_jira_env):
        """Test create_issue handles API error."""
        jira.set_jira_value("summary", "Test Issue")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "feature")
        jira.set_jira_value("benefit", "value")

        mock_module = MagicMock()
        mock_module.post.side_effect = Exception("API Error")
        with patch.object(create_commands, "_get_requests", return_value=mock_module):
            with pytest.raises(SystemExit) as exc_info:
                jira.create_issue()
            assert exc_info.value.code == 1
