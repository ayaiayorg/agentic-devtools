"""Tests for patch_thread_status function."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.helpers import patch_thread_status


class TestPatchThreadStatus:
    """Tests for patch_thread_status function."""

    def _make_config(self) -> AzureDevOpsConfig:
        return AzureDevOpsConfig(
            organization="https://dev.azure.com/myorg",
            project="MyProject",
            repository="MyRepo",
        )

    def test_dry_run_returns_empty_dict(self, capsys):
        """Should return {} and print a dry-run message without calling the API."""
        mock_requests = MagicMock()
        config = self._make_config()

        result = patch_thread_status(
            requests_module=mock_requests,
            headers={"Authorization": "Basic test"},
            config=config,
            repo_id="repo-123",
            pull_request_id=42,
            thread_id=7,
            status="closed",
            dry_run=True,
        )

        assert result == {}
        mock_requests.patch.assert_not_called()
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out
        assert "42" in captured.out

    def test_dry_run_message_contains_status(self, capsys):
        """Should include the status value in the dry-run message."""
        mock_requests = MagicMock()
        config = self._make_config()

        patch_thread_status(
            requests_module=mock_requests,
            headers={},
            config=config,
            repo_id="repo-123",
            pull_request_id=1,
            thread_id=2,
            status="active",
            dry_run=True,
        )

        captured = capsys.readouterr()
        assert "active" in captured.out

    def test_success_returns_response_json(self, mock_azure_devops_env):
        """Should return the parsed JSON response on a successful PATCH."""
        expected_data = {"id": 7, "status": "closed"}
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        mock_requests.patch.return_value = mock_response

        config = self._make_config()

        result = patch_thread_status(
            requests_module=mock_requests,
            headers={"Authorization": "Basic test"},
            config=config,
            repo_id="repo-123",
            pull_request_id=42,
            thread_id=7,
            status="closed",
        )

        assert result == expected_data
        mock_requests.patch.assert_called_once()

    def test_sends_correct_status_in_body(self, mock_azure_devops_env):
        """Should send the status value in the request body."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests.patch.return_value = mock_response

        config = self._make_config()

        patch_thread_status(
            requests_module=mock_requests,
            headers={},
            config=config,
            repo_id="repo-123",
            pull_request_id=42,
            thread_id=7,
            status="active",
        )

        call_kwargs = mock_requests.patch.call_args[1]
        assert call_kwargs["json"]["status"] == "active"

    def test_url_targets_thread_endpoint(self, mock_azure_devops_env):
        """Should build a URL that targets the thread (not comments) endpoint."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests.patch.return_value = mock_response

        config = self._make_config()

        patch_thread_status(
            requests_module=mock_requests,
            headers={},
            config=config,
            repo_id="repo-123",
            pull_request_id=42,
            thread_id=7,
            status="closed",
        )

        url = mock_requests.patch.call_args[0][0]
        assert "threads/7" in url
        assert "comments" not in url

    def test_retries_on_429_then_succeeds(self, mock_azure_devops_env):
        """Should retry after receiving a 429 response and succeed on the next attempt."""
        mock_requests = MagicMock()
        rate_limited_response = MagicMock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {"Retry-After": "2"}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"id": 7}
        mock_requests.patch.side_effect = [rate_limited_response, success_response]

        config = self._make_config()

        with patch("agentic_devtools.cli.azure_devops.helpers.time.sleep") as mock_sleep:
            result = patch_thread_status(
                requests_module=mock_requests,
                headers={},
                config=config,
                repo_id="repo-123",
                pull_request_id=42,
                thread_id=7,
                status="closed",
            )

        assert result == {"id": 7}
        assert mock_requests.patch.call_count == 2
        mock_sleep.assert_called_once_with(2)

    def test_raises_on_429_after_max_retries(self, mock_azure_devops_env):
        """Should raise after exhausting all retries on persistent 429 responses."""
        mock_requests = MagicMock()
        rate_limited_response = MagicMock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {"Retry-After": "1"}
        rate_limited_response.raise_for_status.side_effect = Exception("429 Too Many Requests")
        mock_requests.patch.return_value = rate_limited_response

        config = self._make_config()

        with patch("agentic_devtools.cli.azure_devops.helpers.time.sleep"):
            with pytest.raises(Exception, match="429 Too Many Requests"):
                patch_thread_status(
                    requests_module=mock_requests,
                    headers={},
                    config=config,
                    repo_id="repo-123",
                    pull_request_id=42,
                    thread_id=7,
                    status="closed",
                )

    def test_uses_default_retry_after_when_header_missing(self, mock_azure_devops_env):
        """Should use a default sleep of 60 seconds when Retry-After header is absent."""
        mock_requests = MagicMock()
        rate_limited_response = MagicMock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {}
        mock_requests.patch.side_effect = [rate_limited_response, success_response]

        config = self._make_config()

        with patch("agentic_devtools.cli.azure_devops.helpers.time.sleep") as mock_sleep:
            patch_thread_status(
                requests_module=mock_requests,
                headers={},
                config=config,
                repo_id="repo-123",
                pull_request_id=42,
                thread_id=7,
                status="closed",
            )

        mock_sleep.assert_called_once_with(60)

    def test_uses_default_retry_after_when_header_non_numeric(self, mock_azure_devops_env):
        """Should fall back to 60s when Retry-After header contains a non-numeric value."""
        mock_requests = MagicMock()
        rate_limited_response = MagicMock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {"Retry-After": "Thu, 01 Jan 2099 00:00:00 GMT"}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {}
        mock_requests.patch.side_effect = [rate_limited_response, success_response]

        config = self._make_config()

        with patch("agentic_devtools.cli.azure_devops.helpers.time.sleep") as mock_sleep:
            patch_thread_status(
                requests_module=mock_requests,
                headers={},
                config=config,
                repo_id="repo-123",
                pull_request_id=42,
                thread_id=7,
                status="closed",
            )

        mock_sleep.assert_called_once_with(60)

    def test_raises_on_non_429_error(self, mock_azure_devops_env):
        """Should raise immediately for non-429 HTTP errors (e.g., 403, 500)."""
        mock_requests = MagicMock()
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.raise_for_status.side_effect = Exception("500 Internal Server Error")
        mock_requests.patch.return_value = error_response

        config = self._make_config()

        with pytest.raises(Exception, match="500 Internal Server Error"):
            patch_thread_status(
                requests_module=mock_requests,
                headers={},
                config=config,
                repo_id="repo-123",
                pull_request_id=42,
                thread_id=7,
                status="closed",
            )

        assert mock_requests.patch.call_count == 1
