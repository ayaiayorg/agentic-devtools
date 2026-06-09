"""Tests for get_pull_request_details function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.helpers import get_pull_request_details


class TestGetPullRequestDetails:
    """Tests for get_pull_request_details function."""

    def test_returns_none_when_request_fails(self, mock_azure_devops_env):
        """Should return None when the HTTP request returns a non-200 status."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                return_value="repo-123",
            ):
                result = get_pull_request_details(pull_request_id=42)

        assert result is None

    def test_returns_pr_data_on_success(self, mock_azure_devops_env):
        """Should return parsed PR data when the request succeeds."""
        pr_data = {"pullRequestId": 42, "title": "Test PR", "sourceRefName": "refs/heads/feature/test"}
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = pr_data
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                return_value="repo-123",
            ):
                result = get_pull_request_details(pull_request_id=42)

        assert result is not None
        assert result["pullRequestId"] == 42

    def test_returns_none_when_repository_id_lookup_fails(self, mock_azure_devops_env):
        """Should return None when get_repository_id raises RuntimeError."""
        mock_requests = MagicMock()

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                side_effect=RuntimeError("repo not found"),
            ):
                result = get_pull_request_details(pull_request_id=42)

        assert result is None

    def test_returns_none_on_request_exception(self, mock_azure_devops_env):
        """Should return None when requests.get raises an exception."""
        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("connection timeout")

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                return_value="repo-123",
            ):
                result = get_pull_request_details(pull_request_id=42)

        assert result is None

    def test_uses_provided_config_and_headers(self, mock_azure_devops_env):
        """Should use provided config and headers instead of defaults."""
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig

        config = AzureDevOpsConfig(
            organization="https://dev.azure.com/myorg",
            project="MyProject",
            repository="MyRepo",
        )
        headers = {"Authorization": "Basic dGVzdA=="}

        pr_data = {"pullRequestId": 42, "title": "Test PR"}
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = pr_data
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.helpers.get_repository_id",
                return_value="repo-123",
            ):
                result = get_pull_request_details(pull_request_id=42, config=config, headers=headers)

        assert result is not None
        assert result["pullRequestId"] == 42
