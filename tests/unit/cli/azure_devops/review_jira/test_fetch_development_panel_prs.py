"""
Tests for review_jira module.
"""

import os
from unittest.mock import MagicMock, patch


class TestFetchDevelopmentPanelPrs:
    """Tests for fetch_development_panel_prs function."""

    def test_returns_empty_list_when_no_pat(self, capsys):
        """Test that empty list is returned when no PAT is set."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            fetch_development_panel_prs,
        )

        with patch.dict(os.environ, {}, clear=True):
            result = fetch_development_panel_prs("DFLY-1234", verbose=True)
            assert result == []
            captured = capsys.readouterr()
            assert "JIRA_COPILOT_PAT" in captured.out

    @patch("agentic_devtools.cli.azure_devops.review_jira.requests.get")
    def test_returns_empty_list_when_issue_fetch_fails(self, mock_get, capsys):
        """Test that empty list is returned when issue fetch fails."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            fetch_development_panel_prs,
        )

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with patch.dict(os.environ, {"JIRA_COPILOT_PAT": "test-token"}):
            result = fetch_development_panel_prs("DFLY-9999", verbose=True)
            assert result == []
            captured = capsys.readouterr()
            assert "Failed to fetch issue ID" in captured.out

    @patch("agentic_devtools.cli.azure_devops.review_jira.requests.get")
    def test_returns_empty_list_when_issue_id_missing(self, mock_get, capsys):
        """Test that empty list is returned when issue ID is missing."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            fetch_development_panel_prs,
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "DFLY-1234"}  # No "id" field
        mock_get.return_value = mock_response

        with patch.dict(os.environ, {"JIRA_COPILOT_PAT": "test-token"}):
            result = fetch_development_panel_prs("DFLY-1234", verbose=True)
            assert result == []
            captured = capsys.readouterr()
            assert "Issue ID not found" in captured.out

    @patch("agentic_devtools.cli.azure_devops.review_jira.requests.get")
    def test_returns_empty_list_when_dev_status_fails(self, mock_get, capsys):
        """Test that empty list is returned when dev-status API fails."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            fetch_development_panel_prs,
        )

        # First call returns issue ID, second call fails
        issue_response = MagicMock()
        issue_response.status_code = 200
        issue_response.json.return_value = {"id": "12345"}

        dev_response = MagicMock()
        dev_response.status_code = 500

        mock_get.side_effect = [issue_response, dev_response]

        with patch.dict(os.environ, {"JIRA_COPILOT_PAT": "test-token"}):
            result = fetch_development_panel_prs("DFLY-1234", verbose=True)
            assert result == []
            captured = capsys.readouterr()
            assert "500" in captured.out

    @patch("agentic_devtools.cli.azure_devops.review_jira.requests.get")
    def test_returns_pull_requests_on_success(self, mock_get, capsys):
        """Test that PRs are returned on success."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            fetch_development_panel_prs,
        )

        # First call returns issue ID
        issue_response = MagicMock()
        issue_response.status_code = 200
        issue_response.json.return_value = {"id": "12345"}

        # Second call returns dev-status data
        dev_response = MagicMock()
        dev_response.status_code = 200
        dev_response.json.return_value = {
            "detail": [
                {
                    "pullRequests": [
                        {
                            "id": "#1234",
                            "url": "https://dev.azure.com/org/project/_git/repo/pullrequest/1234",
                            "status": "OPEN",
                        }
                    ]
                }
            ]
        }

        mock_get.side_effect = [issue_response, dev_response]

        with patch.dict(os.environ, {"JIRA_COPILOT_PAT": "test-token"}):
            result = fetch_development_panel_prs("DFLY-1234", verbose=True)
            assert len(result) == 1
            assert result[0]["url"] == "https://dev.azure.com/org/project/_git/repo/pullrequest/1234"
            captured = capsys.readouterr()
            assert "1 PR(s)" in captured.out

    @patch("agentic_devtools.cli.azure_devops.review_jira.requests.get")
    def test_returns_empty_list_when_no_prs(self, mock_get):
        """Test that empty list is returned when no PRs exist."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            fetch_development_panel_prs,
        )

        # First call returns issue ID
        issue_response = MagicMock()
        issue_response.status_code = 200
        issue_response.json.return_value = {"id": "12345"}

        # Second call returns empty dev-status data
        dev_response = MagicMock()
        dev_response.status_code = 200
        dev_response.json.return_value = {"detail": []}

        mock_get.side_effect = [issue_response, dev_response]

        with patch.dict(os.environ, {"JIRA_COPILOT_PAT": "test-token"}):
            result = fetch_development_panel_prs("DFLY-1234")
            assert result == []

    @patch("agentic_devtools.cli.azure_devops.review_jira.requests.get")
    def test_handles_request_exception(self, mock_get, capsys):
        """Test that request exceptions are handled."""
        import requests

        from agentic_devtools.cli.azure_devops.review_jira import (
            fetch_development_panel_prs,
        )

        mock_get.side_effect = requests.RequestException("Connection error")

        with patch.dict(os.environ, {"JIRA_COPILOT_PAT": "test-token"}):
            result = fetch_development_panel_prs("DFLY-1234", verbose=True)
            assert result == []
            captured = capsys.readouterr()
            assert "Failed to fetch development panel" in captured.out
