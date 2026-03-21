"""Tests for agentic_devtools.tools.jira.fetch_issue_context."""

from unittest.mock import MagicMock

import pytest

from agentic_devtools.tools.jira import JiraConfig, fetch_issue_context


class TestFetchIssueContext:
    """Tests for the fetch_issue_context tool function."""

    def _make_config(self, mock_requests=None, base_url="https://jira.example.com"):
        return JiraConfig(
            base_url=base_url,
            headers={"Authorization": "Basic xxx"},
            ssl_verify=False,
            requests_module=mock_requests or MagicMock(),
        )

    def _make_issue_response(self, issue_key="PROJ-1", is_subtask=False, epic_link=None, parent_key=None):
        fields = {
            "summary": "Test issue",
            "description": "Description",
            "comment": {"comments": []},
            "labels": [],
            "issuetype": {
                "name": "Sub-task" if is_subtask else "Task",
                "subtask": is_subtask,
            },
            "customfield_10008": epic_link,
        }
        if parent_key and is_subtask:
            fields["parent"] = {"key": parent_key}
        return {"key": issue_key, "fields": fields}

    def test_returns_issue_data(self):
        mock_requests = MagicMock()
        issue_data = self._make_issue_response("PROJ-1")
        mock_response = MagicMock()
        mock_response.json.return_value = issue_data
        mock_requests.get.return_value = mock_response

        config = self._make_config(mock_requests)
        result = fetch_issue_context(config=config, issue_key="PROJ-1")

        assert result["issue"]["key"] == "PROJ-1"
        assert result["parent_issue"] is None
        assert result["epic_issue"] is None
        assert result["remote_links"] == []

    def test_raises_value_error_on_empty_base_url(self):
        config = self._make_config(base_url="")

        with pytest.raises(ValueError, match="base_url is required"):
            fetch_issue_context(config=config, issue_key="PROJ-1")

    def test_fetches_parent_for_subtask(self):
        mock_requests = MagicMock()
        issue_data = self._make_issue_response("PROJ-2", is_subtask=True, parent_key="PROJ-1")
        parent_data = {"key": "PROJ-1", "fields": {"summary": "Parent Issue"}}

        def get_side_effect(url, **kwargs):
            resp = MagicMock()
            if "PROJ-2" in url and "remotelink" not in url:
                resp.json.return_value = issue_data
            elif "PROJ-1" in url:
                resp.json.return_value = parent_data
            else:
                resp.json.return_value = []
            return resp

        mock_requests.get.side_effect = get_side_effect
        config = self._make_config(mock_requests)

        result = fetch_issue_context(config=config, issue_key="PROJ-2")

        assert result["parent_issue"] is not None
        assert result["parent_issue"]["key"] == "PROJ-1"

    def test_fetches_epic_for_linked_issue(self):
        mock_requests = MagicMock()
        issue_data = self._make_issue_response("PROJ-3", epic_link="PROJ-100")
        epic_data = {"key": "PROJ-100", "fields": {"summary": "My Epic"}}

        def get_side_effect(url, **kwargs):
            resp = MagicMock()
            if "PROJ-3" in url and "remotelink" not in url:
                resp.json.return_value = issue_data
            elif "PROJ-100" in url:
                resp.json.return_value = epic_data
            else:
                resp.json.return_value = []
            return resp

        mock_requests.get.side_effect = get_side_effect
        config = self._make_config(mock_requests)

        result = fetch_issue_context(config=config, issue_key="PROJ-3")

        assert result["epic_issue"] is not None
        assert result["epic_issue"]["key"] == "PROJ-100"

    def test_no_epic_fetch_for_subtask(self):
        """Subtasks should not trigger an epic fetch even if customfield_10008 is set."""
        mock_requests = MagicMock()
        issue_data = self._make_issue_response("PROJ-4", is_subtask=True, parent_key="PROJ-3", epic_link="PROJ-100")

        def get_side_effect(url, **kwargs):
            resp = MagicMock()
            if "PROJ-4" in url and "remotelink" not in url:
                resp.json.return_value = issue_data
            elif "PROJ-3" in url:
                resp.json.return_value = {"key": "PROJ-3", "fields": {"summary": "Parent"}}
            else:
                resp.json.return_value = []
            return resp

        mock_requests.get.side_effect = get_side_effect
        config = self._make_config(mock_requests)

        result = fetch_issue_context(config=config, issue_key="PROJ-4")

        assert result["epic_issue"] is None

    def test_no_epic_fetch_for_epic_itself(self):
        """Epics themselves should not trigger a recursive epic fetch."""
        mock_requests = MagicMock()
        issue_data = {
            "key": "PROJ-100",
            "fields": {
                "summary": "An Epic",
                "description": "",
                "comment": {"comments": []},
                "labels": [],
                "issuetype": {"name": "Epic", "subtask": False},
                "customfield_10008": "PROJ-200",
            },
        }

        def get_side_effect(url, **kwargs):
            resp = MagicMock()
            if "PROJ-100" in url and "remotelink" not in url:
                resp.json.return_value = issue_data
            else:
                resp.json.return_value = []
            return resp

        mock_requests.get.side_effect = get_side_effect
        config = self._make_config(mock_requests)

        result = fetch_issue_context(config=config, issue_key="PROJ-100")

        assert result["epic_issue"] is None

    def test_remote_links_returned(self):
        mock_requests = MagicMock()
        issue_data = self._make_issue_response("PROJ-5")
        links = [{"object": {"title": "PR #1"}}]

        def get_side_effect(url, **kwargs):
            resp = MagicMock()
            if "remotelink" in url:
                resp.json.return_value = links
            else:
                resp.json.return_value = issue_data
            return resp

        mock_requests.get.side_effect = get_side_effect
        config = self._make_config(mock_requests)

        result = fetch_issue_context(config=config, issue_key="PROJ-5")

        assert len(result["remote_links"]) == 1
        assert result["remote_links"][0]["object"]["title"] == "PR #1"

    def test_handles_fetch_failure_gracefully(self):
        """Parent/epic fetch failures should not crash the function."""
        mock_requests = MagicMock()
        issue_data = self._make_issue_response("PROJ-6", is_subtask=True, parent_key="PROJ-5")

        call_count = 0

        def get_side_effect(url, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            if "PROJ-6" in url and "remotelink" not in url:
                resp.json.return_value = issue_data
            elif "PROJ-5" in url:
                raise Exception("Connection refused")
            else:
                resp.json.return_value = []
            return resp

        mock_requests.get.side_effect = get_side_effect
        config = self._make_config(mock_requests)

        result = fetch_issue_context(config=config, issue_key="PROJ-6")

        assert result["parent_issue"] is None  # Fetch failed gracefully

    def test_calls_raise_for_status_on_main_issue(self):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")
        mock_requests.get.return_value = mock_response
        config = self._make_config(mock_requests)

        with pytest.raises(Exception, match="HTTP 404"):
            fetch_issue_context(config=config, issue_key="PROJ-1")
