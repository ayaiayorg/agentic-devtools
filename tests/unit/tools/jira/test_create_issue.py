"""Tests for agentic_devtools.tools.jira.create_issue."""

from unittest.mock import MagicMock

import pytest

from agentic_devtools.tools.jira import JiraConfig, create_issue


class TestCreateIssue:
    """Tests for the create_issue tool function."""

    def _make_config(self, mock_requests=None, base_url="https://jira.example.com"):
        return JiraConfig(
            base_url=base_url,
            headers={"Authorization": "Basic xxx"},
            ssl_verify=False,
            requests_module=mock_requests or MagicMock(),
        )

    def test_returns_issue_key_and_url(self):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "PROJ-123", "id": "10001"}
        mock_requests.post.return_value = mock_response
        config = self._make_config(mock_requests)

        result = create_issue(
            config=config,
            project_key="PROJ",
            summary="Test issue",
            issue_type="Task",
            description="A description",
            labels=["label1"],
        )

        assert result["issue_key"] == "PROJ-123"
        assert result["url"] == "https://jira.example.com/browse/PROJ-123"
        assert result["raw_response"]["key"] == "PROJ-123"

    def test_raises_value_error_on_empty_base_url(self):
        config = self._make_config(base_url="")

        with pytest.raises(ValueError, match="base_url is required"):
            create_issue(
                config=config,
                project_key="PROJ",
                summary="Test",
                issue_type="Task",
                description="Desc",
                labels=[],
            )

    def test_posts_correct_payload(self):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "PROJ-1"}
        mock_requests.post.return_value = mock_response
        config = self._make_config(mock_requests)

        create_issue(
            config=config,
            project_key="PROJ",
            summary="My summary",
            issue_type="Bug",
            description="Bug description",
            labels=["bug", "urgent"],
        )

        call_args = mock_requests.post.call_args
        assert "rest/api/2/issue" in call_args[0][0]
        payload = call_args[1]["json"]
        assert payload["fields"]["project"]["key"] == "PROJ"
        assert payload["fields"]["summary"] == "My summary"
        assert payload["fields"]["issuetype"]["name"] == "Bug"
        assert payload["fields"]["labels"] == ["bug", "urgent"]

    def test_adds_epic_name_for_epic_type(self):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "PROJ-1"}
        mock_requests.post.return_value = mock_response
        config = self._make_config(mock_requests)

        create_issue(
            config=config,
            project_key="PROJ",
            summary="Epic",
            issue_type="Epic",
            description="Epic desc",
            labels=[],
            epic_name="My Epic Name",
        )

        payload = mock_requests.post.call_args[1]["json"]
        assert payload["fields"]["customfield_10006"] == "My Epic Name"

    def test_adds_parent_for_subtask(self):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "PROJ-2"}
        mock_requests.post.return_value = mock_response
        config = self._make_config(mock_requests)

        create_issue(
            config=config,
            project_key="PROJ",
            summary="Subtask",
            issue_type="Sub-task",
            description="Subtask desc",
            labels=[],
            parent_key="PROJ-1",
        )

        payload = mock_requests.post.call_args[1]["json"]
        assert payload["fields"]["parent"]["key"] == "PROJ-1"

    def test_calls_raise_for_status(self):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 400")
        mock_requests.post.return_value = mock_response
        config = self._make_config(mock_requests)

        with pytest.raises(Exception, match="HTTP 400"):
            create_issue(
                config=config,
                project_key="PROJ",
                summary="Test",
                issue_type="Task",
                description="Desc",
                labels=[],
            )

    def test_handles_missing_key_in_response(self):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "10001"}
        mock_requests.post.return_value = mock_response
        config = self._make_config(mock_requests)

        result = create_issue(
            config=config,
            project_key="PROJ",
            summary="Test",
            issue_type="Task",
            description="Desc",
            labels=[],
        )

        assert result["issue_key"] == ""
        assert result["url"] == ""

    def test_raises_value_error_epic_without_epic_name(self):
        config = self._make_config()

        with pytest.raises(ValueError, match="epic_name is required"):
            create_issue(
                config=config,
                project_key="PROJ",
                summary="Epic",
                issue_type="Epic",
                description="Desc",
                labels=[],
            )

    def test_raises_value_error_subtask_without_parent_key(self):
        config = self._make_config()

        with pytest.raises(ValueError, match="parent_key is required"):
            create_issue(
                config=config,
                project_key="PROJ",
                summary="Subtask",
                issue_type="Sub-task",
                description="Desc",
                labels=[],
            )

    def test_no_epic_name_for_non_epic(self):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "PROJ-1"}
        mock_requests.post.return_value = mock_response
        config = self._make_config(mock_requests)

        create_issue(
            config=config,
            project_key="PROJ",
            summary="Task",
            issue_type="Task",
            description="Task desc",
            labels=[],
            epic_name="Should be ignored",
        )

        payload = mock_requests.post.call_args[1]["json"]
        assert "customfield_10006" not in payload["fields"]

    def test_no_parent_for_non_subtask(self):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "PROJ-1"}
        mock_requests.post.return_value = mock_response
        config = self._make_config(mock_requests)

        create_issue(
            config=config,
            project_key="PROJ",
            summary="Task",
            issue_type="Task",
            description="Task desc",
            labels=[],
            parent_key="PROJ-0",
        )

        payload = mock_requests.post.call_args[1]["json"]
        assert "parent" not in payload["fields"]

    def test_uses_config_ssl_verify(self):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "PROJ-1"}
        mock_requests.post.return_value = mock_response
        config = JiraConfig(
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            ssl_verify="/path/to/ca-bundle.pem",
            requests_module=mock_requests,
        )

        create_issue(
            config=config,
            project_key="PROJ",
            summary="Task",
            issue_type="Task",
            description="Desc",
            labels=[],
        )

        call_kwargs = mock_requests.post.call_args[1]
        assert call_kwargs["verify"] == "/path/to/ca-bundle.pem"
