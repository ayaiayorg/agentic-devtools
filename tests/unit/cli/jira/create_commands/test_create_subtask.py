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


class TestCreateSubtaskDryRun:
    """Tests for create_subtask command in dry run mode."""

    def test_create_subtask_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test create_subtask in dry run mode."""
        jira.set_jira_value("parent_key", "DFLY-1234")
        jira.set_jira_value("summary", "Test Subtask")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "subtask work")
        jira.set_jira_value("benefit", "progress")
        jira.set_jira_value("dry_run", True)

        jira.create_subtask()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "DFLY-1234" in captured.out
        assert "Test Subtask" in captured.out

    def test_create_subtask_missing_parent(self, temp_state_dir, clear_state_before):
        """Test create_subtask fails with missing parent_key."""
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "work")
        jira.set_jira_value("benefit", "progress")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_subtask()
        assert exc_info.value.code == 1

    def test_create_subtask_missing_summary(self, temp_state_dir, clear_state_before):
        """Test create_subtask fails with missing summary."""
        jira.set_jira_value("parent_key", "DFLY-1234")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "work")
        jira.set_jira_value("benefit", "progress")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_subtask()
        assert exc_info.value.code == 1

    def test_create_subtask_missing_role(self, temp_state_dir, clear_state_before):
        """Test create_subtask fails with missing role."""
        jira.set_jira_value("parent_key", "DFLY-1234")
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("desired_outcome", "work")
        jira.set_jira_value("benefit", "progress")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_subtask()
        assert exc_info.value.code == 1

    def test_create_subtask_missing_desired_outcome(self, temp_state_dir, clear_state_before):
        """Test create_subtask fails with missing desired_outcome."""
        jira.set_jira_value("parent_key", "DFLY-1234")
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("benefit", "progress")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_subtask()
        assert exc_info.value.code == 1

    def test_create_subtask_missing_benefit(self, temp_state_dir, clear_state_before):
        """Test create_subtask fails with missing benefit."""
        jira.set_jira_value("parent_key", "DFLY-1234")
        jira.set_jira_value("summary", "Test")
        jira.set_jira_value("role", "dev")
        jira.set_jira_value("desired_outcome", "work")

        with pytest.raises(SystemExit) as exc_info:
            jira.create_subtask()
        assert exc_info.value.code == 1


class TestCreateSubtaskWithMock:
    """Tests for create_subtask with mocked API calls."""

    def test_create_subtask_success(
        self,
        temp_state_dir,
        clear_state_before,
        mock_jira_env,
        mock_requests_module,
        capsys,
    ):
        """Test successful subtask creation."""
        jira.set_jira_value("parent_key", "DFLY-1234")
        jira.set_jira_value("summary", "Test Subtask")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "subtask work")
        jira.set_jira_value("benefit", "progress")

        jira.create_subtask()

        captured = capsys.readouterr()
        assert "DFLY-9999" in captured.out
        assert "Sub-task created successfully" in captured.out

    def test_create_subtask_api_error(self, temp_state_dir, clear_state_before, mock_jira_env):
        """Test create_subtask handles API error."""
        jira.set_jira_value("parent_key", "DFLY-1234")
        jira.set_jira_value("summary", "Test Subtask")
        jira.set_jira_value("role", "developer")
        jira.set_jira_value("desired_outcome", "subtask work")
        jira.set_jira_value("benefit", "progress")

        mock_module = MagicMock()
        mock_module.post.side_effect = Exception("API Error")
        with patch.object(create_commands, "_get_requests", return_value=mock_module):
            with pytest.raises(SystemExit) as exc_info:
                jira.create_subtask()
            assert exc_info.value.code == 1
