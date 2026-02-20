"""Tests for CreatePlaceholderIssue."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import (
    create_placeholder_issue,
)


class TestCreatePlaceholderIssue:
    """Tests for create_placeholder_issue function."""

    @patch("agentic_devtools.cli.jira.create_commands.create_issue_sync")
    def test_creates_task_successfully(self, mock_create):
        """Test creating a placeholder task successfully."""
        mock_create.return_value = {"key": "DFLY-1234"}

        result = create_placeholder_issue(project_key="DFLY", issue_type="Task")

        assert result.success is True
        assert result.issue_key == "DFLY-1234"
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["project_key"] == "DFLY"
        assert call_kwargs["issue_type"] == "Task"
        assert "placeholder" in call_kwargs["summary"].lower()

    @patch("agentic_devtools.cli.jira.create_commands.create_issue_sync")
    def test_creates_epic_with_epic_name(self, mock_create):
        """Test creating a placeholder epic with epic name."""
        mock_create.return_value = {"key": "DFLY-5678"}

        result = create_placeholder_issue(project_key="DFLY", issue_type="Epic")

        assert result.success is True
        assert result.issue_key == "DFLY-5678"
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["issue_type"] == "Epic"
        assert call_kwargs["epic_name"] is not None

    @patch("agentic_devtools.cli.jira.create_commands.create_issue_sync")
    def test_creates_subtask_with_parent(self, mock_create):
        """Test creating a placeholder subtask with parent key."""
        mock_create.return_value = {"key": "DFLY-1235"}

        result = create_placeholder_issue(
            project_key="DFLY",
            issue_type="Sub-task",
            parent_key="DFLY-1234",
        )

        assert result.success is True
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["parent_key"] == "DFLY-1234"

    @patch("agentic_devtools.cli.jira.create_commands.create_issue_sync")
    def test_handles_missing_key_in_response(self, mock_create):
        """Test handling response without issue key."""
        mock_create.return_value = {}  # No key in response

        result = create_placeholder_issue(project_key="DFLY")

        assert result.success is False
        assert "did not return" in result.error_message.lower()

    @patch("agentic_devtools.cli.jira.create_commands.create_issue_sync")
    def test_handles_api_exception(self, mock_create):
        """Test handling API exception."""
        mock_create.side_effect = Exception("API connection failed")

        result = create_placeholder_issue(project_key="DFLY")

        assert result.success is False
        assert "API connection failed" in result.error_message
