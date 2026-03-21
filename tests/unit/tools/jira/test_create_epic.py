"""Tests for agentic_devtools.tools.jira.create_epic."""

from unittest.mock import MagicMock, patch

from agentic_devtools.tools.jira import JiraConfig, create_epic


class TestCreateEpic:
    """Tests for the create_epic convenience wrapper."""

    def _make_config(self, mock_requests=None):
        return JiraConfig(
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            ssl_verify=False,
            requests_module=mock_requests or MagicMock(),
        )

    def test_calls_create_issue_with_epic_type(self):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "PROJ-10"}
        mock_requests.post.return_value = mock_response
        config = self._make_config(mock_requests)

        result = create_epic(
            config=config,
            project_key="PROJ",
            summary="My Epic",
            epic_name="Epic Name",
            description="Epic description",
            labels=["epic-label"],
        )

        assert result["issue_key"] == "PROJ-10"
        payload = mock_requests.post.call_args[1]["json"]
        assert payload["fields"]["issuetype"]["name"] == "Epic"
        assert payload["fields"]["customfield_10006"] == "Epic Name"

    @patch("agentic_devtools.tools.jira.create_issue")
    def test_delegates_to_create_issue(self, mock_create_issue):
        mock_create_issue.return_value = {
            "issue_key": "PROJ-1",
            "url": "https://jira.example.com/browse/PROJ-1",
            "raw_response": {},
        }
        config = self._make_config()

        create_epic(
            config=config,
            project_key="PROJ",
            summary="Epic",
            epic_name="Name",
            description="Desc",
            labels=[],
        )

        mock_create_issue.assert_called_once_with(
            config=config,
            project_key="PROJ",
            summary="Epic",
            issue_type="Epic",
            description="Desc",
            labels=[],
            epic_name="Name",
        )
