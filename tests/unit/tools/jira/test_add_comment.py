"""Tests for agentic_devtools.tools.jira.add_comment."""

from unittest.mock import MagicMock

import pytest

from agentic_devtools.tools.jira import JiraConfig, add_comment


class TestAddComment:
    """Tests for the add_comment tool function."""

    def _make_config(self, mock_requests=None, base_url="https://jira.example.com"):
        return JiraConfig(
            base_url=base_url,
            headers={"Authorization": "Basic xxx"},
            ssl_verify=False,
            requests_module=mock_requests or MagicMock(),
        )

    def test_returns_comment_id(self):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "54321", "body": "My comment"}
        mock_requests.post.return_value = mock_response
        config = self._make_config(mock_requests)

        result = add_comment(config=config, issue_key="PROJ-123", comment="My comment")

        assert result["comment_id"] == "54321"
        assert result["raw_response"]["body"] == "My comment"

    def test_raises_value_error_on_empty_base_url(self):
        config = self._make_config(base_url="")

        with pytest.raises(ValueError, match="base_url is required"):
            add_comment(config=config, issue_key="PROJ-123", comment="Test")

    def test_posts_correct_payload(self):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "1"}
        mock_requests.post.return_value = mock_response
        config = self._make_config(mock_requests)

        add_comment(config=config, issue_key="DFLY-456", comment="Hello world")

        call_args = mock_requests.post.call_args
        assert "DFLY-456/comment" in call_args[0][0]
        assert call_args[1]["json"]["body"] == "Hello world"

    def test_calls_raise_for_status(self):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 403")
        mock_requests.post.return_value = mock_response
        config = self._make_config(mock_requests)

        with pytest.raises(Exception, match="HTTP 403"):
            add_comment(config=config, issue_key="PROJ-1", comment="Test")

    def test_handles_missing_id_in_response(self):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": "Test"}
        mock_requests.post.return_value = mock_response
        config = self._make_config(mock_requests)

        result = add_comment(config=config, issue_key="PROJ-1", comment="Test")

        assert result["comment_id"] == ""
