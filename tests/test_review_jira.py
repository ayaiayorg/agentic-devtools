"""
Tests for review_jira module.
"""

import os
from unittest.mock import MagicMock, patch


class TestGetJiraCredentials:
    """Tests for get_jira_credentials function."""

    def test_returns_pat_from_environment(self):
        """Test that PAT is returned from environment variable."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import get_jira_credentials

        with patch.dict(os.environ, {"JIRA_COPILOT_PAT": "test-token"}):
            pat, base_url = get_jira_credentials()
            assert pat == "test-token"

    def test_returns_none_when_pat_not_set(self):
        """Test that None is returned when PAT is not set."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import get_jira_credentials

        with patch.dict(os.environ, {}, clear=True):
            pat, base_url = get_jira_credentials()
            assert pat is None

    def test_returns_default_base_url(self):
        """Test that default base URL is returned."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import get_jira_credentials

        with patch.dict(os.environ, {}, clear=True):
            pat, base_url = get_jira_credentials()
            assert base_url == "https://jira.swica.ch"

    def test_returns_custom_base_url(self):
        """Test that custom base URL is returned."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import get_jira_credentials

        with patch.dict(os.environ, {"JIRA_BASE_URL": "https://jira.example.com/"}):
            pat, base_url = get_jira_credentials()
            assert base_url == "https://jira.example.com"


class TestFetchJiraIssue:
    """Tests for fetch_jira_issue function."""

    def test_returns_none_when_no_pat(self, capsys):
        """Test that None is returned when no PAT is set."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import fetch_jira_issue

        with patch.dict(os.environ, {}, clear=True):
            result = fetch_jira_issue("DFLY-1234", verbose=True)
            assert result is None
            captured = capsys.readouterr()
            assert "JIRA_COPILOT_PAT" in captured.out

    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.requests.get")
    def test_returns_issue_data_on_success(self, mock_get):
        """Test that issue data is returned on success."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import fetch_jira_issue

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

    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.requests.get")
    def test_returns_none_on_error_status(self, mock_get, capsys):
        """Test that None is returned on error status."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import fetch_jira_issue

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with patch.dict(os.environ, {"JIRA_COPILOT_PAT": "test-token"}):
            result = fetch_jira_issue("DFLY-9999", verbose=True)
            assert result is None
            captured = capsys.readouterr()
            assert "404" in captured.out

    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.requests.get")
    def test_handles_request_exception(self, mock_get, capsys):
        """Test that request exceptions are handled."""
        import requests

        from agdt_ai_helpers.cli.azure_devops.review_jira import fetch_jira_issue

        mock_get.side_effect = requests.RequestException("Connection error")

        with patch.dict(os.environ, {"JIRA_COPILOT_PAT": "test-token"}):
            result = fetch_jira_issue("DFLY-1234", verbose=True)
            assert result is None
            captured = capsys.readouterr()
            assert "Failed" in captured.out


class TestExtractLinkedPrFromIssue:
    """Tests for extract_linked_pr_from_issue function."""

    def test_returns_none_for_none_input(self):
        """Test that None is returned for None input."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            extract_linked_pr_from_issue,
        )

        result = extract_linked_pr_from_issue(None)
        assert result is None

    def test_extracts_pr_from_comments(self):
        """Test extracting PR ID from comments."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            extract_linked_pr_from_issue,
        )

        issue_data = {"fields": {"comment": {"comments": [{"body": "Created Pull Request #1234"}]}}}

        result = extract_linked_pr_from_issue(issue_data)
        assert result == 1234

    def test_extracts_pr_with_asterisks(self):
        """Test extracting PR ID with Jira markup asterisks."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            extract_linked_pr_from_issue,
        )

        issue_data = {"fields": {"comment": {"comments": [{"body": "*PR:* #5678"}]}}}

        result = extract_linked_pr_from_issue(issue_data)
        assert result == 5678

    def test_extracts_latest_pr_first(self):
        """Test that the latest PR is extracted first."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            extract_linked_pr_from_issue,
        )

        issue_data = {
            "fields": {
                "comment": {
                    "comments": [
                        {"body": "Pull Request #1111"},
                        {"body": "Pull Request #2222"},
                    ]
                }
            }
        }

        result = extract_linked_pr_from_issue(issue_data)
        assert result == 2222

    def test_falls_back_to_description(self):
        """Test falling back to description when no comments have PR."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            extract_linked_pr_from_issue,
        )

        issue_data = {
            "fields": {
                "description": "See PR #3333 for changes",
                "comment": {"comments": []},
            }
        }

        result = extract_linked_pr_from_issue(issue_data)
        assert result == 3333

    def test_returns_none_when_no_pr_found(self):
        """Test that None is returned when no PR is found."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            extract_linked_pr_from_issue,
        )

        issue_data = {"fields": {"description": "No PR here", "comment": {"comments": []}}}

        result = extract_linked_pr_from_issue(issue_data)
        assert result is None

    def test_handles_missing_comment_field(self):
        """Test handling missing comment field."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            extract_linked_pr_from_issue,
        )

        issue_data = {"fields": {}}

        result = extract_linked_pr_from_issue(issue_data)
        assert result is None


class TestGetLinkedPullRequestFromJira:
    """Tests for get_linked_pull_request_from_jira function."""

    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.fetch_jira_issue")
    def test_returns_pr_id_from_issue(self, mock_fetch):
        """Test returning PR ID from issue."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            get_linked_pull_request_from_jira,
        )

        mock_fetch.return_value = {"fields": {"comment": {"comments": [{"body": "PR #4444"}]}}}

        result = get_linked_pull_request_from_jira("DFLY-1234")
        assert result == 4444

    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.fetch_jira_issue")
    def test_returns_none_when_fetch_fails(self, mock_fetch):
        """Test returning None when fetch fails."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            get_linked_pull_request_from_jira,
        )

        mock_fetch.return_value = None

        result = get_linked_pull_request_from_jira("DFLY-1234")
        assert result is None


class TestDisplayJiraIssueSummary:
    """Tests for display_jira_issue_summary function."""

    def test_does_nothing_for_none_input(self, capsys):
        """Test that nothing is printed for None input."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            display_jira_issue_summary,
        )

        display_jira_issue_summary(None)

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_prints_issue_summary(self, capsys):
        """Test printing issue summary."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            display_jira_issue_summary,
        )

        issue_data = {
            "key": "DFLY-1234",
            "fields": {
                "summary": "Test issue",
                "issuetype": {"name": "Story"},
                "status": {"name": "In Progress"},
                "labels": ["backend", "api"],
            },
        }

        display_jira_issue_summary(issue_data)

        captured = capsys.readouterr()
        assert "DFLY-1234" in captured.out
        assert "Test issue" in captured.out
        assert "Story" in captured.out
        assert "In Progress" in captured.out
        assert "backend" in captured.out

    def test_handles_missing_fields(self, capsys):
        """Test handling missing fields."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            display_jira_issue_summary,
        )

        issue_data = {"key": "DFLY-5678", "fields": {}}

        display_jira_issue_summary(issue_data)

        captured = capsys.readouterr()
        assert "DFLY-5678" in captured.out
        assert "Unknown" in captured.out


class TestFetchAndDisplayJiraIssue:
    """Tests for fetch_and_display_jira_issue function."""

    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.fetch_jira_issue")
    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.display_jira_issue_summary")
    def test_fetches_and_displays_issue(self, mock_display, mock_fetch):
        """Test fetching and displaying issue."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            fetch_and_display_jira_issue,
        )

        mock_fetch.return_value = {"key": "DFLY-1234"}

        result = fetch_and_display_jira_issue("DFLY-1234")

        assert result == {"key": "DFLY-1234"}
        mock_display.assert_called_once_with({"key": "DFLY-1234"})

    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.fetch_jira_issue")
    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.display_jira_issue_summary")
    def test_does_not_display_when_fetch_fails(self, mock_display, mock_fetch):
        """Test that display is not called when fetch fails."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            fetch_and_display_jira_issue,
        )

        mock_fetch.return_value = None

        result = fetch_and_display_jira_issue("DFLY-1234")

        assert result is None
        mock_display.assert_not_called()


class TestFetchDevelopmentPanelPrs:
    """Tests for fetch_development_panel_prs function."""

    def test_returns_empty_list_when_no_pat(self, capsys):
        """Test that empty list is returned when no PAT is set."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            fetch_development_panel_prs,
        )

        with patch.dict(os.environ, {}, clear=True):
            result = fetch_development_panel_prs("DFLY-1234", verbose=True)
            assert result == []
            captured = capsys.readouterr()
            assert "JIRA_COPILOT_PAT" in captured.out

    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.requests.get")
    def test_returns_empty_list_when_issue_fetch_fails(self, mock_get, capsys):
        """Test that empty list is returned when issue fetch fails."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
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

    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.requests.get")
    def test_returns_empty_list_when_issue_id_missing(self, mock_get, capsys):
        """Test that empty list is returned when issue ID is missing."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
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

    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.requests.get")
    def test_returns_empty_list_when_dev_status_fails(self, mock_get, capsys):
        """Test that empty list is returned when dev-status API fails."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
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

    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.requests.get")
    def test_returns_pull_requests_on_success(self, mock_get, capsys):
        """Test that PRs are returned on success."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
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

    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.requests.get")
    def test_returns_empty_list_when_no_prs(self, mock_get):
        """Test that empty list is returned when no PRs exist."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
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

    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.requests.get")
    def test_handles_request_exception(self, mock_get, capsys):
        """Test that request exceptions are handled."""
        import requests

        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            fetch_development_panel_prs,
        )

        mock_get.side_effect = requests.RequestException("Connection error")

        with patch.dict(os.environ, {"JIRA_COPILOT_PAT": "test-token"}):
            result = fetch_development_panel_prs("DFLY-1234", verbose=True)
            assert result == []
            captured = capsys.readouterr()
            assert "Failed to fetch development panel" in captured.out


class TestExtractPrIdFromDevelopmentPanel:
    """Tests for extract_pr_id_from_development_panel function."""

    def test_returns_none_for_empty_list(self):
        """Test that None is returned for empty list."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            extract_pr_id_from_development_panel,
        )

        result = extract_pr_id_from_development_panel([])
        assert result is None

    def test_extracts_pr_id_from_ado_url(self):
        """Test extracting PR ID from Azure DevOps URL."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            extract_pr_id_from_development_panel,
        )

        pull_requests = [{"url": "https://dev.azure.com/org/project/_git/repo/pullrequest/5678"}]

        result = extract_pr_id_from_development_panel(pull_requests)
        assert result == 5678

    def test_extracts_pr_id_from_direct_id_field(self):
        """Test extracting PR ID from direct id field."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            extract_pr_id_from_development_panel,
        )

        pull_requests = [{"id": 9999}]

        result = extract_pr_id_from_development_panel(pull_requests)
        assert result == 9999

    def test_extracts_pr_id_from_string_id_field(self):
        """Test extracting PR ID from string id field like '#1234'."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            extract_pr_id_from_development_panel,
        )

        pull_requests = [{"id": "#1234"}]

        result = extract_pr_id_from_development_panel(pull_requests)
        assert result == 1234

    def test_returns_first_pr_when_multiple(self):
        """Test that first PR is returned when multiple exist."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            extract_pr_id_from_development_panel,
        )

        pull_requests = [
            {"url": "https://dev.azure.com/org/project/_git/repo/pullrequest/1111"},
            {"url": "https://dev.azure.com/org/project/_git/repo/pullrequest/2222"},
        ]

        result = extract_pr_id_from_development_panel(pull_requests)
        assert result == 1111

    def test_returns_none_when_no_valid_url_or_id(self):
        """Test that None is returned when no valid URL or ID exists."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            extract_pr_id_from_development_panel,
        )

        pull_requests = [{"status": "OPEN", "title": "Some PR"}]

        result = extract_pr_id_from_development_panel(pull_requests)
        assert result is None


class TestGetPrFromDevelopmentPanel:
    """Tests for get_pr_from_development_panel function."""

    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.fetch_development_panel_prs")
    def test_returns_pr_id_from_development_panel(self, mock_fetch):
        """Test returning PR ID from development panel."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            get_pr_from_development_panel,
        )

        mock_fetch.return_value = [{"url": "https://dev.azure.com/org/project/_git/repo/pullrequest/7777"}]

        result = get_pr_from_development_panel("DFLY-1234")
        assert result == 7777
        mock_fetch.assert_called_once_with("DFLY-1234", False)

    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.fetch_development_panel_prs")
    def test_returns_none_when_no_prs(self, mock_fetch):
        """Test returning None when no PRs in development panel."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            get_pr_from_development_panel,
        )

        mock_fetch.return_value = []

        result = get_pr_from_development_panel("DFLY-1234")
        assert result is None

    @patch("agdt_ai_helpers.cli.azure_devops.review_jira.fetch_development_panel_prs")
    def test_passes_verbose_flag(self, mock_fetch):
        """Test that verbose flag is passed through."""
        from agdt_ai_helpers.cli.azure_devops.review_jira import (
            get_pr_from_development_panel,
        )

        mock_fetch.return_value = []

        get_pr_from_development_panel("DFLY-1234", verbose=True)
        mock_fetch.assert_called_once_with("DFLY-1234", True)
