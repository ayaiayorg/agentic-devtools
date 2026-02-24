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
    role_commands,
    update_commands,
)


@pytest.fixture
def mock_jira_env():
    """Set up environment variables for Jira API calls.

    Sets JIRA_COPILOT_PAT for authentication and JIRA_SSL_VERIFY=0 to
    prevent _get_ssl_verify() from attempting external certificate fetching
    (which would make tests slow and network-dependent).
    """
    with patch.dict(
        "os.environ",
        {
            "JIRA_COPILOT_PAT": "test-token",
            "JIRA_SSL_VERIFY": "0",
        },
    ):
        yield


@pytest.fixture
def mock_requests_module():
    """Mock the requests module for Jira API calls.

    Patches _get_requests in all Jira implementation modules that call it
    (create_commands, comment_commands, get_commands, update_commands,
    role_commands) and returns a mock HTTP client pre-configured with a
    default success response.
    """
    mock_module = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"key": "DFLY-9999", "id": "12345"}
    mock_response.raise_for_status = MagicMock()
    mock_module.post.return_value = mock_response
    mock_module.get.return_value = mock_response
    with patch.object(create_commands, "_get_requests", return_value=mock_module):
        with patch.object(comment_commands, "_get_requests", return_value=mock_module):
            with patch.object(get_commands, "_get_requests", return_value=mock_module):
                with patch.object(update_commands, "_get_requests", return_value=mock_module):
                    with patch.object(role_commands, "_get_requests", return_value=mock_module):
                        yield mock_module
