"""Tests for create_issue_sync function."""

from agdt_ai_helpers.cli import jira


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
