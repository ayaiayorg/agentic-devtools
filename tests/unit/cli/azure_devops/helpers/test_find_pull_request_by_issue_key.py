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
                result = find_pull_request_by_issue_key("PROJECT-9999")

        assert result is None

    def test_returns_none_when_prs_exist_but_none_match(self, mock_azure_devops_env):
        """Should return None when PRs exist but none match the issue key."""
        pr_data = {
            "pullRequestId": 1,
            "sourceRefName": "refs/heads/feature/OTHER-111",
            "title": "Unrelated PR",
            "description": "No match here",
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
                result = find_pull_request_by_issue_key("PROJECT-9999")

        assert result is None

    def test_returns_matching_pr(self, mock_azure_devops_env):
        """Should return the matching PR dict when issue key appears in the source branch."""
        pr_data = {
            "pullRequestId": 42,
            "sourceRefName": "refs/heads/feature/PROJECT-1234/my-feature",
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
                result = find_pull_request_by_issue_key("PROJECT-1234")

        assert result is not None
        assert result["pullRequestId"] == 42

    def test_returns_none_on_http_error(self, mock_azure_devops_env):
        """Should return None when the HTTP request returns a non-200 status."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                return_value="repo-123",
            ):
                result = find_pull_request_by_issue_key("PROJECT-1234")

        assert result is None

    def test_returns_most_recent_when_multiple_match(self, mock_azure_devops_env):
        """Should return the most recently created PR when multiple match."""
        pr_old = {
            "pullRequestId": 10,
            "sourceRefName": "refs/heads/feature/PROJECT-1234/old",
            "title": "Old PR",
            "description": "",
            "creationDate": "2024-01-01T00:00:00Z",
        }
        pr_new = {
            "pullRequestId": 20,
            "sourceRefName": "refs/heads/feature/PROJECT-1234/new",
            "title": "New PR",
            "description": "",
            "creationDate": "2024-06-01T00:00:00Z",
        }
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [pr_old, pr_new]}
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                return_value="repo-123",
            ):
                result = find_pull_request_by_issue_key("PROJECT-1234")

        assert result is not None
        assert result["pullRequestId"] == 20

    def test_uses_provided_config_and_headers(self, mock_azure_devops_env):
        """Should use provided config and headers instead of defaults."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/myorg",
            project="MyProject",
            repository="MyRepo",
        )
        headers = {"Authorization": "Basic dGVzdA=="}

        pr_data = {
            "pullRequestId": 99,
            "sourceRefName": "refs/heads/feature/PROJECT-5555",
            "title": "Test",
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
                result = find_pull_request_by_issue_key("PROJECT-5555", config=config, headers=headers)

        assert result is not None
        assert result["pullRequestId"] == 99
