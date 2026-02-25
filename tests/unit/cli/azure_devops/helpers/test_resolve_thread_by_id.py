"""Tests for resolve_thread_by_id function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.helpers import resolve_thread_by_id
from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig


class TestResolveThreadById:
    """Tests for resolve_thread_by_id function."""

    def test_calls_patch_request(self, mock_azure_devops_env):
        """Should make a PATCH request to update the thread status."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.patch.return_value = mock_response

        config = MagicMock(spec=AzureDevOpsConfig)
        config.org_url = "https://dev.azure.com/myorg"
        config.project = "MyProject"

        resolve_thread_by_id(
            requests_module=mock_requests,
            headers={"Authorization": "Basic test"},
            config=config,
            repo_id="repo-123",
            pull_request_id=42,
            thread_id=7,
            status="closed",
        )

        mock_requests.patch.assert_called_once()

    def test_sends_correct_status_in_payload(self, mock_azure_devops_env):
        """Should send the correct status value in the request body."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.patch.return_value = mock_response

        config = MagicMock(spec=AzureDevOpsConfig)
        config.org_url = "https://dev.azure.com/myorg"
        config.project = "MyProject"

        resolve_thread_by_id(
            requests_module=mock_requests,
            headers={"Authorization": "Basic test"},
            config=config,
            repo_id="repo-123",
            pull_request_id=42,
            thread_id=7,
            status="fixed",
        )

        call_kwargs = mock_requests.patch.call_args[1]
        assert call_kwargs.get("json", {}).get("status") == "fixed"
