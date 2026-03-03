"""Tests for fetch_jira_issue function."""

import os
from unittest.mock import MagicMock, patch


class TestFetchJiraIssue:
    """Tests for fetch_jira_issue function."""

    def test_returns_none_when_no_pat(self, capsys):
        """Test that None is returned when no PAT is set."""
        from agentic_devtools.cli.azure_devops.review_jira import fetch_jira_issue

        with patch.dict(os.environ, {}, clear=True):
            result = fetch_jira_issue("DFLY-1234", verbose=True)
            assert result is None
            captured = capsys.readouterr()
            assert "JIRA_COPILOT_PAT" in captured.out

    @patch("agentic_devtools.cli.azure_devops.review_jira.requests.get")
    def test_returns_issue_data_on_success(self, mock_get):
        """Test that issue data is returned on success."""
        from agentic_devtools.cli.azure_devops.review_jira import fetch_jira_issue

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "key": "DFLY-1234",
            "fields": {"summary": "Test"},
        }
        mock_get.return_value = mock_response

        with patch.dict(os.environ, {"JIRA_COPILOT_PAT": "test-token"}):
            result = fetch_jira_issue("DFLY-1234")
            assert result == {"key": "DFLY-1234", "fields": {"summary": "Test"}}

    @patch("agentic_devtools.cli.azure_devops.review_jira._get_jira_ssl_verify", return_value=True)
    @patch("agentic_devtools.cli.azure_devops.review_jira.requests.get")
    def test_passes_verify_to_requests_get(self, mock_get, mock_ssl_verify):
        """Test that verify= is passed to requests.get."""
        from agentic_devtools.cli.azure_devops.review_jira import fetch_jira_issue

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "DFLY-1234", "fields": {}}
        mock_get.return_value = mock_response

        with patch.dict(os.environ, {"JIRA_COPILOT_PAT": "test-token"}):
            fetch_jira_issue("DFLY-1234")

        call_kwargs = mock_get.call_args.kwargs
        assert "verify" in call_kwargs

    @patch("agentic_devtools.cli.azure_devops.review_jira.requests.get")
    def test_returns_none_on_error_status(self, mock_get, capsys):
        """Test that None is returned on error status."""
        from agentic_devtools.cli.azure_devops.review_jira import fetch_jira_issue

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with patch.dict(os.environ, {"JIRA_COPILOT_PAT": "test-token"}):
            result = fetch_jira_issue("DFLY-9999", verbose=True)
            assert result is None
            captured = capsys.readouterr()
            assert "404" in captured.out

    @patch("agentic_devtools.cli.azure_devops.review_jira.requests.get")
    def test_handles_request_exception(self, mock_get, capsys):
        """Test that request exceptions are handled."""
        import requests

        from agentic_devtools.cli.azure_devops.review_jira import fetch_jira_issue

        mock_get.side_effect = requests.RequestException("Connection error")

        with patch.dict(os.environ, {"JIRA_COPILOT_PAT": "test-token"}):
            result = fetch_jira_issue("DFLY-1234", verbose=True)
            assert result is None
            captured = capsys.readouterr()
            assert "Failed" in captured.out
