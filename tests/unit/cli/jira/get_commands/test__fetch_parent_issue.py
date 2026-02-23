"""
Tests for Jira CLI commands (create_epic, create_issue, create_subtask, add_comment, get_issue).

These tests validate the command-line interface functions that create and manage Jira issues.
They use mocked API calls to avoid network dependencies.
"""

from unittest.mock import MagicMock, patch

import pytest

from agdt_ai_helpers.cli.jira import (
    comment_commands,
    create_commands,
    get_commands,
)


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


class TestFetchParentIssue:
    """Tests for _fetch_parent_issue helper function."""

    def test_fetch_parent_issue_success(self, mock_jira_env):
        """Test _fetch_parent_issue returns parent data on success."""
        mock_module = MagicMock()
        mock_response = MagicMock()
        parent_data = {
            "key": "DFLY-1234",
            "fields": {"summary": "Parent Issue"},
        }
        mock_response.json.return_value = parent_data
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        result = get_commands._fetch_parent_issue(
            mock_module, "https://jira.example.com", "DFLY-1234", {"Authorization": "Basic xxx"}
        )

        assert result == parent_data

    def test_fetch_parent_issue_returns_none_on_error(self, mock_jira_env, capsys):
        """Test _fetch_parent_issue returns None on API error."""
        mock_module = MagicMock()
        mock_module.get.side_effect = Exception("Network error")

        result = get_commands._fetch_parent_issue(
            mock_module, "https://jira.example.com", "DFLY-1234", {"Authorization": "Basic xxx"}
        )

        assert result is None
        captured = capsys.readouterr()
        assert "Warning: Could not fetch parent issue DFLY-1234" in captured.err
