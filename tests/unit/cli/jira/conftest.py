"""
Shared fixtures for tests/unit/cli/jira/.

Provides mock fixtures for Jira API interactions used across multiple
test modules, eliminating duplication of fixture definitions.
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
    """Set up environment variables for Jira API calls."""
    with patch.dict("os.environ", {"JIRA_COPILOT_PAT": "test-token"}):
        yield


@pytest.fixture
def mock_requests_module():
    """Mock the requests module for Jira API calls.

    Patches _get_requests in all Jira implementation modules and returns
    a mock HTTP client pre-configured with a default success response.
    """
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
