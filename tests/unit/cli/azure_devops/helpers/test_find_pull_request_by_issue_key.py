"""Tests for find_pull_request_by_issue_key function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.helpers import find_pull_request_by_issue_key


class TestFindPullRequestByIssueKey:
    """Tests for find_pull_request_by_issue_key function."""

    def test_returns_none_when_no_prs_found(self, mock_azure_devops_env):
        """Should return None when no pull requests match the issue key."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": []}
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                return_value="repo-123",
            ):
                result = find_pull_request_by_issue_key("DFLY-9999")

        assert result is None

    def test_returns_matching_pr(self, mock_azure_devops_env):
        """Should return the matching PR dict when issue key appears in the source branch."""
        pr_data = {
            "pullRequestId": 42,
            "sourceRefName": "refs/heads/feature/DFLY-1234/my-feature",
            "title": "My PR",
            "description": "",
            "creationDate": "2024-01-01T00:00:00Z",
        }
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [pr_data]}
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                return_value="repo-123",
            ):
                result = find_pull_request_by_issue_key("DFLY-1234")

        assert result is not None
        assert result["pullRequestId"] == 42
