"""Tests for agentic_devtools.adapters.jira_adapter.JiraAdapter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agentic_devtools.adapters.jira_adapter import JiraAdapter
from agentic_devtools.tools.jira import JiraConfig


def _make_config(mock_requests: MagicMock | None = None, base_url: str = "https://jira.example.com") -> JiraConfig:
    """Build a JiraConfig with an injectable mock requests module."""
    return JiraConfig(
        base_url=base_url,
        headers={"Authorization": "Basic xxx"},
        ssl_verify=False,
        requests_module=mock_requests or MagicMock(),
    )


class TestJiraAdapter:
    """Tests for the JiraAdapter concrete implementation."""

    def test_constructor_raises_on_empty_project_key(self) -> None:
        """Raises ValueError when project_key is empty and create_issue is called."""
        adapter = JiraAdapter(config=_make_config(), project_key="")
        with pytest.raises(ValueError, match="project_key"):
            adapter.create_issue("Title", "Desc")

    def test_constructor_accepts_none_project_key(self) -> None:
        """Constructor accepts None project_key for read-only operations."""
        adapter = JiraAdapter(config=_make_config(), project_key=None)
        # Should not raise — only create_issue needs project_key
        assert adapter._project_key == ""

    def test_create_issue_raises_without_project_key(self) -> None:
        """create_issue raises ValueError when project_key was not provided."""
        adapter = JiraAdapter(config=_make_config())
        with pytest.raises(ValueError, match="project_key"):
            adapter.create_issue("Title", "Desc")

    def test_get_issue_works_without_project_key(self) -> None:
        """get_issue works even when project_key is not set."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "fields": {"summary": "Issue"},
        }
        mock_requests.get.return_value = mock_response

        adapter = JiraAdapter(config=_make_config(mock_requests))
        detail = adapter.get_issue("PROJ-1")
        assert detail["title"] == "Issue"

    def test_add_comment_works_without_project_key(self) -> None:
        """add_comment works even when project_key is not set."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "555"}
        mock_requests.post.return_value = mock_response

        adapter = JiraAdapter(config=_make_config(mock_requests))
        result = adapter.add_comment("PROJ-1", "Hello")
        assert result["comment_id"] == "555"

    def test_create_issue_delegates_and_maps_result(self) -> None:
        """create_issue calls jira.create_issue and maps to IssueResult."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "PROJ-42"}
        mock_requests.post.return_value = mock_response

        adapter = JiraAdapter(config=_make_config(mock_requests), project_key="PROJ")
        result = adapter.create_issue("My title", "My description", labels=["bug"])

        assert result["issue_id"] == "PROJ-42"
        assert result["url"] == "https://jira.example.com/browse/PROJ-42"

    def test_create_issue_without_labels(self) -> None:
        """create_issue passes empty list when labels is None."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "PROJ-1"}
        mock_requests.post.return_value = mock_response

        adapter = JiraAdapter(config=_make_config(mock_requests), project_key="PROJ")
        result = adapter.create_issue("Title", "Desc")

        assert result["issue_id"] == "PROJ-1"
        call_kwargs = mock_requests.post.call_args[1]
        assert call_kwargs["json"]["fields"]["labels"] == []

    def test_get_issue_maps_fields(self) -> None:
        """get_issue maps Jira fields to IssueDetail."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "fields": {
                "summary": "Test issue",
                "description": "A description",
                "labels": ["bug", "urgent"],
                "status": {"name": "Open"},
                "issuetype": {"subtask": False},
                "comment": {
                    "comments": [
                        {"id": "100", "body": "First comment", "created": "2026-01-01T00:00:00Z"},
                    ],
                },
            },
        }
        mock_requests.get.return_value = mock_response

        adapter = JiraAdapter(config=_make_config(mock_requests), project_key="PROJ")
        detail = adapter.get_issue("PROJ-42")

        assert detail["issue_id"] == "PROJ-42"
        assert detail["title"] == "Test issue"
        assert detail["description"] == "A description"
        assert detail["labels"] == ["bug", "urgent"]
        assert detail["status"] == "Open"
        assert detail["url"] == "https://jira.example.com/browse/PROJ-42"
        assert len(detail["comments"]) == 1
        assert detail["comments"][0]["comment_id"] == "100"
        assert detail["comments"][0]["body"] == "First comment"

    def test_get_issue_handles_missing_optional_fields(self) -> None:
        """get_issue defaults gracefully when optional fields are absent."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "fields": {
                "summary": "Minimal issue",
            },
        }
        mock_requests.get.return_value = mock_response

        adapter = JiraAdapter(config=_make_config(mock_requests), project_key="PROJ")
        detail = adapter.get_issue("PROJ-99")

        assert detail["title"] == "Minimal issue"
        assert detail["description"] == ""
        assert detail["labels"] == []
        assert detail["status"] == ""
        assert detail["comments"] == []

    def test_get_issue_handles_none_description(self) -> None:
        """get_issue converts None description to empty string."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "fields": {
                "summary": "Issue",
                "description": None,
            },
        }
        mock_requests.get.return_value = mock_response

        adapter = JiraAdapter(config=_make_config(mock_requests), project_key="PROJ")
        detail = adapter.get_issue("PROJ-1")
        assert detail["description"] == ""

    def test_get_issue_handles_non_dict_status(self) -> None:
        """get_issue handles non-dict status field gracefully."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "fields": {
                "summary": "Issue",
                "status": "not-a-dict",
            },
        }
        mock_requests.get.return_value = mock_response

        adapter = JiraAdapter(config=_make_config(mock_requests), project_key="PROJ")
        detail = adapter.get_issue("PROJ-1")
        assert detail["status"] == ""

    def test_get_issue_handles_non_dict_comment(self) -> None:
        """get_issue handles non-dict comment field gracefully."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "fields": {
                "summary": "Issue",
                "comment": "not-a-dict",
            },
        }
        mock_requests.get.return_value = mock_response

        adapter = JiraAdapter(config=_make_config(mock_requests), project_key="PROJ")
        detail = adapter.get_issue("PROJ-1")
        assert detail["comments"] == []

    def test_get_issue_handles_null_labels(self) -> None:
        """get_issue normalizes null labels to empty list."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "fields": {
                "summary": "Issue",
                "labels": None,
            },
        }
        mock_requests.get.return_value = mock_response

        adapter = JiraAdapter(config=_make_config(mock_requests), project_key="PROJ")
        detail = adapter.get_issue("PROJ-1")
        assert detail["labels"] == []

    def test_get_issue_filters_non_string_labels(self) -> None:
        """get_issue filters out non-string entries from labels list."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "fields": {
                "summary": "Issue",
                "labels": ["bug", 42, "feature", None],
            },
        }
        mock_requests.get.return_value = mock_response

        adapter = JiraAdapter(config=_make_config(mock_requests), project_key="PROJ")
        detail = adapter.get_issue("PROJ-1")
        assert detail["labels"] == ["bug", "feature"]

    def test_add_comment_delegates_and_maps_result(self) -> None:
        """add_comment calls jira.add_comment and maps to CommentResult."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "555"}
        mock_requests.post.return_value = mock_response

        adapter = JiraAdapter(config=_make_config(mock_requests), project_key="PROJ")
        result = adapter.add_comment("PROJ-42", "Hello world")

        assert result["comment_id"] == "555"

    def test_list_issues_raises_not_implemented(self) -> None:
        """list_issues raises NotImplementedError."""
        adapter = JiraAdapter(config=_make_config(), project_key="PROJ")
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            adapter.list_issues()

    def test_custom_issue_type(self) -> None:
        """Constructor accepts a custom issue_type."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "PROJ-1"}
        mock_requests.post.return_value = mock_response

        adapter = JiraAdapter(config=_make_config(mock_requests), project_key="PROJ", issue_type="Bug")
        adapter.create_issue("Bug title", "Bug desc")

        call_kwargs = mock_requests.post.call_args[1]
        assert call_kwargs["json"]["fields"]["issuetype"]["name"] == "Bug"
