"""
Tests for Jira CLI commands (create_epic, create_issue, create_subtask, add_comment, get_issue).

These tests validate the command-line interface functions that create and manage Jira issues.
They use mocked API calls to avoid network dependencies.
"""

from unittest.mock import MagicMock, patch

import pytest

from agdt_ai_helpers import state
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


class TestFetchRemoteLinks:
    """Tests for _fetch_remote_links function."""

    def test_returns_empty_list_on_exception(self, mock_jira_env):
        """Test _fetch_remote_links returns empty list on API error."""
        mock_module = MagicMock()
        mock_module.get.side_effect = Exception("Network error")

        result = get_commands._fetch_remote_links(
            mock_module, "https://jira.example.com", "DFLY-1234", {"Authorization": "Basic xxx"}
        )

        assert result == []

    def test_returns_empty_list_for_non_list_response(self, mock_jira_env):
        """Test _fetch_remote_links handles non-list response."""
        mock_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "not a list"}
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        result = get_commands._fetch_remote_links(
            mock_module, "https://jira.example.com", "DFLY-1234", {"Authorization": "Basic xxx"}
        )

        assert result == []

    def test_returns_list_of_remote_links(self, mock_jira_env):
        """Test _fetch_remote_links returns list of links."""
        mock_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"object": {"title": "Link 1"}},
            {"object": {"title": "Link 2"}},
        ]
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        result = get_commands._fetch_remote_links(
            mock_module, "https://jira.example.com", "DFLY-1234", {"Authorization": "Basic xxx"}
        )

        assert len(result) == 2

