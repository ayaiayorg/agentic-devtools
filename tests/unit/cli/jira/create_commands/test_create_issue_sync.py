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


class TestCreateIssueSyncWithMock:
    """Tests for create_issue_sync with mocked API calls."""

    def test_create_issue_sync_success(self, mock_jira_env, mock_requests_module):
        """Test successful issue creation."""
        result = jira.create_issue_sync(
            project_key="DFLY",
            summary="Test Issue",
            issue_type="Task",
            description="Test description",
            labels=["test-label"],
        )

        assert result["key"] == "DFLY-9999"
        mock_requests_module.post.assert_called_once()
        call_args = mock_requests_module.post.call_args
        assert "issue" in call_args[0][0]

    def test_create_issue_sync_with_epic_name(self, mock_jira_env, mock_requests_module):
        """Test issue creation with epic name field."""
        jira.create_issue_sync(
            project_key="DFLY",
            summary="Test Epic",
            issue_type="Epic",
            description="Epic description",
            labels=["epic-label"],
            epic_name="TEST-EPIC",
        )

        call_args = mock_requests_module.post.call_args
        payload = call_args[1]["json"]
        assert jira.EPIC_NAME_FIELD in payload["fields"]
        assert payload["fields"][jira.EPIC_NAME_FIELD] == "TEST-EPIC"

    def test_create_issue_sync_with_parent_key(self, mock_jira_env, mock_requests_module):
        """Test subtask creation with parent key."""
        jira.create_issue_sync(
            project_key="DFLY",
            summary="Test Subtask",
            issue_type="Sub-task",
            description="Subtask description",
            labels=["subtask-label"],
            parent_key="DFLY-1234",
        )

        call_args = mock_requests_module.post.call_args
        payload = call_args[1]["json"]
        assert payload["fields"]["parent"]["key"] == "DFLY-1234"

    def test_create_issue_sync_subtask_variant(self, mock_jira_env, mock_requests_module):
        """Test subtask creation with lowercase 'subtask' type."""
        jira.create_issue_sync(
            project_key="DFLY",
            summary="Test Subtask",
            issue_type="subtask",
            description="Subtask description",
            labels=[],
            parent_key="DFLY-5678",
        )

        call_args = mock_requests_module.post.call_args
        payload = call_args[1]["json"]
        assert payload["fields"]["parent"]["key"] == "DFLY-5678"



class TestCreateIssueSyncEdgeCases:
    """Edge case tests for create_issue_sync."""

    def test_create_issue_sync_no_epic_name_for_epic(self, mock_jira_env, mock_requests_module):
        """Test creating Epic without epic_name doesn't add field."""
        jira.create_issue_sync(
            project_key="DFLY",
            summary="Test Epic",
            issue_type="Epic",
            description="Epic description",
            labels=[],
            epic_name=None,
        )

        call_args = mock_requests_module.post.call_args
        payload = call_args[1]["json"]
        assert jira.EPIC_NAME_FIELD not in payload["fields"]

    def test_create_issue_sync_no_parent_for_task(self, mock_jira_env, mock_requests_module):
        """Test creating Task with parent_key doesn't add parent field."""
        jira.create_issue_sync(
            project_key="DFLY",
            summary="Test Task",
            issue_type="Task",
            description="Task description",
            labels=[],
            parent_key="DFLY-1234",  # Should be ignored for non-subtask
        )

        call_args = mock_requests_module.post.call_args
        payload = call_args[1]["json"]
        assert "parent" not in payload["fields"]

