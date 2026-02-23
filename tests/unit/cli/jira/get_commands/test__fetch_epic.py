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


class TestFetchEpic:
    """Tests for _fetch_epic helper function."""

    def test_fetch_epic_success(self, mock_jira_env):
        """Test _fetch_epic returns epic data on success."""
        mock_module = MagicMock()
        mock_response = MagicMock()
        epic_data = {
            "key": "DFLY-100",
            "fields": {"summary": "Epic for Testing", "issuetype": {"name": "Epic"}},
        }
        mock_response.json.return_value = epic_data
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        result = get_commands._fetch_epic(
            mock_module, "https://jira.example.com", "DFLY-100", {"Authorization": "Basic xxx"}
        )

        assert result == epic_data
        mock_module.get.assert_called_once()
        call_url = mock_module.get.call_args[0][0]
        assert "DFLY-100" in call_url
        assert "customfield_10008" in call_url

    def test_fetch_epic_returns_none_on_error(self, mock_jira_env, capsys):
        """Test _fetch_epic returns None on API error."""
        mock_module = MagicMock()
        mock_module.get.side_effect = Exception("Network error")

        result = get_commands._fetch_epic(
            mock_module, "https://jira.example.com", "DFLY-100", {"Authorization": "Basic xxx"}
        )

        assert result is None
        captured = capsys.readouterr()
        assert "Warning: Could not fetch epic DFLY-100" in captured.err
