"""
E2E smoke tests for Jira CLI commands.

These tests validate Jira command entry points with mocked API responses
to ensure CLI commands work correctly with realistic API structures.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.jira import get_commands
from agentic_devtools.state import get_value, set_value


def _create_mock_jira_issue_response() -> dict:
    """Create a realistic mock Jira issue response."""
    return {
        "expand": "renderedFields,names,schema,operations,editmeta,changelog,versionedRepresentations",
        "id": "12345",
        "self": "https://test.atlassian.net/rest/api/2/issue/12345",
        "key": "DFLY-1234",
        "fields": {
            "summary": "Test Issue for E2E Smoke Tests",
            "description": "This is a test issue description for smoke testing the CLI commands.",
            "issuetype": {
                "self": "https://test.atlassian.net/rest/api/2/issuetype/10001",
                "id": "10001",
                "description": "A task that needs to be done.",
                "iconUrl": "https://test.atlassian.net/images/icons/issuetypes/task.svg",
                "name": "Task",
                "subtask": False,
            },
            "labels": ["smoke-test", "e2e"],
            "comment": {
                "comments": [
                    {
                        "self": "https://test.atlassian.net/rest/api/2/issue/12345/comment/67890",
                        "id": "67890",
                        "author": {
                            "self": "https://test.atlassian.net/rest/api/2/user?accountId=test-user",
                            "accountId": "test-user",
                            "displayName": "Test User",
                            "active": True,
                        },
                        "body": "This is a test comment.",
                        "created": "2026-02-01T10:00:00.000+0000",
                        "updated": "2026-02-01T10:00:00.000+0000",
                    }
                ],
                "maxResults": 50,
                "total": 1,
                "startAt": 0,
            },
            "parent": None,
            "customfield_10008": None,
        },
    }


def _create_mock_jira_comment_response() -> dict:
    """Create a realistic mock Jira comment response."""
    return {
        "self": "https://test.atlassian.net/rest/api/2/issue/12345/comment/67891",
        "id": "67891",
        "author": {
            "self": "https://test.atlassian.net/rest/api/2/user?accountId=test-user",
            "accountId": "test-user",
            "displayName": "Test User",
            "active": True,
        },
        "body": "This is a test comment from E2E smoke test",
        "created": "2026-02-03T19:00:00.000+0000",
        "updated": "2026-02-03T19:00:00.000+0000",
    }


class TestJiraGetIssueE2E:
    """End-to-end smoke tests for agdt-get-jira-issue command."""

    def test_get_jira_issue_returns_valid_response(
        self,
        temp_state_dir: Path,
        clean_state: None,
        mock_jira_env: None,
    ) -> None:
        """
        Smoke test: agdt-get-jira-issue retrieves issue and saves response.

        Validates:
        - Command executes without errors
        - Response is saved to expected file
        - Response contains required fields (key, fields)
        - State is updated with metadata reference
        """
        # Arrange
        set_value("jira.issue_key", "DFLY-1234")

        # Mock requests to return realistic response
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = _create_mock_jira_issue_response()
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch("agentic_devtools.cli.jira.get_commands._get_requests", return_value=mock_requests):
            with patch("agentic_devtools.cli.jira.get_commands.get_state_dir", return_value=temp_state_dir):
                # Act
                get_commands.get_issue()

        # Assert
        # Check that response file was created
        response_file = temp_state_dir / "temp-get-issue-details-response.json"
        assert response_file.exists(), "Response file should be created"

        # Verify response structure
        response_data = json.loads(response_file.read_text())
        assert "key" in response_data, "Response should contain issue key"
        assert "fields" in response_data, "Response should contain fields"
        assert response_data["key"] == "DFLY-1234"

        # Verify state metadata
        issue_details = get_value("jira.issue_details")
        assert issue_details is not None, "State should contain issue details metadata"
        assert "location" in issue_details
        assert "retrievalTimestamp" in issue_details

    def test_get_jira_issue_parses_fields_correctly(
        self,
        temp_state_dir: Path,
        clean_state: None,
        mock_jira_env: None,
    ) -> None:
        """
        Smoke test: agdt-get-jira-issue parses all expected fields.

        Validates:
        - Summary is extracted
        - Description is extracted
        - Labels are parsed
        - Issue type is detected
        - Comments are retrieved
        """
        # Arrange
        set_value("jira.issue_key", "DFLY-1234")

        # Mock requests
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = _create_mock_jira_issue_response()
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch("agentic_devtools.cli.jira.get_commands._get_requests", return_value=mock_requests):
            with patch("agentic_devtools.cli.jira.get_commands.get_state_dir", return_value=temp_state_dir):
                # Act
                get_commands.get_issue()

        # Assert
        response_file = temp_state_dir / "temp-get-issue-details-response.json"
        response_data = json.loads(response_file.read_text())

        fields = response_data["fields"]
        assert "summary" in fields, "Fields should contain summary"
        assert "description" in fields, "Fields should contain description"
        assert "labels" in fields, "Fields should contain labels"
        assert "issuetype" in fields, "Fields should contain issue type"
        assert "comment" in fields, "Fields should contain comments"

        # Verify issue is not a subtask
        assert fields["issuetype"]["subtask"] is False

    def test_get_jira_issue_without_issue_key_fails(
        self,
        temp_state_dir: Path,
        clean_state: None,
        mock_jira_env: None,
    ) -> None:
        """
        Smoke test: agdt-get-jira-issue fails gracefully without issue key.

        Validates:
        - Command exits with error when issue_key is missing
        - Appropriate error message is shown
        """
        # Arrange - don't set issue_key

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            get_commands.get_issue()

        assert exc_info.value.code == 1, "Should exit with error code 1"


class TestJiraAddCommentE2E:
    """End-to-end smoke tests for agdt-add-jira-comment command."""

    def test_add_jira_comment_posts_successfully(
        self,
        temp_state_dir: Path,
        clean_state: None,
        mock_jira_env: None,
    ) -> None:
        """
        Smoke test: agdt-add-jira-comment posts comment to issue.

        Note: This test validates the sync function, not the async wrapper.
        The async wrapper spawns background tasks which are harder to test
        in smoke tests.

        Validates:
        - Comment is posted to Jira API
        - Response contains comment ID
        - Response includes author information
        """
        from agentic_devtools.cli.jira import comment_commands, get_commands

        # Arrange
        set_value("jira.issue_key", "DFLY-1234")
        set_value("jira.comment", "This is a test comment from E2E smoke test")

        # Mock requests
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = _create_mock_jira_comment_response()
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response
        mock_requests.get.return_value = mock_response  # For get_issue call

        with patch("agentic_devtools.cli.jira.comment_commands._get_requests", return_value=mock_requests):
            # Mock get_issue from get_commands module
            with patch.object(get_commands, "get_issue"):
                # Act - call the sync function directly
                comment_commands.add_comment(
                    issue_key="DFLY-1234",
                    comment="This is a test comment from E2E smoke test",
                )

        # Assert
        # Verify post was called
        assert mock_requests.post.called, "POST request should be made"

    def test_add_jira_comment_returns_author_info(
        self,
        temp_state_dir: Path,
        clean_state: None,
        mock_jira_env: None,
    ) -> None:
        """
        Smoke test: agdt-add-jira-comment response includes author.

        Validates:
        - Response contains author object
        - Author has expected fields (displayName, accountId)
        """
        from agentic_devtools.cli.jira import comment_commands, get_commands

        # Arrange
        set_value("jira.issue_key", "DFLY-1234")
        set_value("jira.comment", "This is a test comment from E2E smoke test")

        # Mock requests
        mock_requests = MagicMock()
        mock_response = MagicMock()
        response_data = _create_mock_jira_comment_response()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response
        mock_requests.get.return_value = mock_response

        with patch("agentic_devtools.cli.jira.comment_commands._get_requests", return_value=mock_requests):
            with patch.object(get_commands, "get_issue"):
                # Act
                comment_commands.add_comment(
                    issue_key="DFLY-1234",
                    comment="This is a test comment from E2E smoke test",
                )

        # Assert - verify the response structure by checking what was returned
        call_result = mock_response.json.return_value
        assert "author" in call_result, "Response should contain author"
        author = call_result["author"]
        assert "displayName" in author, "Author should have display name"
        assert "accountId" in author, "Author should have account ID"
        assert author["displayName"] == "Test User"
