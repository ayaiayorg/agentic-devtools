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


class TestAddCommentDryRun:
    """Tests for add_comment command in dry run mode."""

    def test_add_comment_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test add_comment in dry run mode."""
        jira.set_jira_value("issue_key", "DFLY-1234")
        jira.set_jira_value("comment", "This is a test comment")
        jira.set_jira_value("dry_run", True)

        jira.add_comment()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "DFLY-1234" in captured.out

    def test_add_comment_missing_issue_key(self, temp_state_dir, clear_state_before):
        """Test add_comment fails with missing issue_key."""
        jira.set_jira_value("comment", "Test comment")

        with pytest.raises(SystemExit) as exc_info:
            jira.add_comment()
        assert exc_info.value.code == 1

    def test_add_comment_missing_comment(self, temp_state_dir, clear_state_before):
        """Test add_comment fails with missing comment."""
        jira.set_jira_value("issue_key", "DFLY-1234")

        with pytest.raises(SystemExit) as exc_info:
            jira.add_comment()
        assert exc_info.value.code == 1


class TestAddCommentWithMock:
    """Tests for add_comment with mocked API calls."""

    def test_add_comment_success(self, temp_state_dir, clear_state_before, mock_jira_env, capsys):
        """Test successful comment addition."""
        jira.set_jira_value("issue_key", "DFLY-1234")
        jira.set_jira_value("comment", "Test comment")

        mock_module = MagicMock()
        # Mock the POST response for adding comment
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {"id": "comment-123"}
        mock_post_response.raise_for_status = MagicMock()
        mock_module.post.return_value = mock_post_response

        # Mock the GET response for refreshing issue details
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Test Issue",
                "description": "Test description",
                "issuetype": {"name": "Task"},
                "labels": ["test"],
                "comment": {"comments": []},
            },
        }
        mock_get_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_get_response

        with patch.object(comment_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "_get_requests", return_value=mock_module):
                with patch.object(get_commands, "get_state_dir", return_value=temp_state_dir):
                    jira.add_comment()

        captured = capsys.readouterr()
        assert "Comment added successfully" in captured.out

    def test_add_comment_api_error(self, temp_state_dir, clear_state_before, mock_jira_env):
        """Test add_comment handles API error."""
        jira.set_jira_value("issue_key", "DFLY-1234")
        jira.set_jira_value("comment", "Test comment")

        mock_module = MagicMock()
        mock_module.post.side_effect = Exception("API Error")
        with patch.object(comment_commands, "_get_requests", return_value=mock_module):
            with pytest.raises(SystemExit) as exc_info:
                jira.add_comment()
            assert exc_info.value.code == 1
