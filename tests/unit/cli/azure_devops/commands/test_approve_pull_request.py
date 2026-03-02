"""Tests for approve_pull_request function."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import azure_devops

# Use string paths for patching to ensure we patch the right location
COMMANDS_MODULE = "agentic_devtools.cli.azure_devops.commands"


class TestApprovePullRequest:
    """Tests for approve_pull_request command."""

    def test_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output."""
        state.set_pull_request_id(12345)
        state.set_value("content", "LGTM!")
        state.set_dry_run(True)

        azure_devops.approve_pull_request()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before):
        """Test raises error when pull request ID is missing."""
        state.set_value("content", "LGTM!")
        with pytest.raises(KeyError, match="pull_request_id"):
            azure_devops.approve_pull_request()


class TestApprovePullRequestActualCall:
    """Tests for approve_pull_request with mocked API calls."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_successful_approval(self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before):
        """Test successful approval."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 123}
        mock_req_module.post.return_value = mock_response
        mock_req_module.patch.return_value = mock_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_value("content", "LGTM!")

        azure_devops.approve_pull_request()

        # Check that approval sentinel was added
        call_args = mock_req_module.post.call_args
        body = call_args[1]["json"]
        content = body["comments"][0]["content"]
        assert azure_devops.APPROVAL_SENTINEL in content


class TestFindSummaryThreadId:
    """Tests for _find_summary_thread_id – review-state.json priority."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    def test_uses_review_state_thread_id_when_available(self, temp_state_dir, clear_state_before):
        """When review-state.json is available it returns overallSummary.threadId directly."""
        from agentic_devtools.cli.azure_devops.commands import _find_summary_thread_id
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig

        mock_review_state = MagicMock()
        mock_review_state.overallSummary = MagicMock()
        mock_review_state.overallSummary.threadId = 162564

        mock_requests = MagicMock()
        mock_config = MagicMock(spec=AzureDevOpsConfig)

        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            return_value=mock_review_state,
        ):
            result = _find_summary_thread_id(mock_requests, {}, mock_config, "repo-id", 25230)

        assert result == 162564
        # Should NOT have made any HTTP requests
        mock_requests.get.assert_not_called()

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    def test_falls_back_to_thread_search_when_review_state_missing(self, temp_state_dir, clear_state_before):
        """Falls back to searching PR threads when review-state.json does not exist."""
        from agentic_devtools.cli.azure_devops.commands import _find_summary_thread_id
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig

        mock_config = MagicMock(spec=AzureDevOpsConfig)
        mock_config.build_api_url.return_value = "https://api/threads"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": 99,
                    "comments": [{"content": "## Overall PR Review Summary\nAll looks good."}],
                }
            ]
        }
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            side_effect=FileNotFoundError("not found"),
        ):
            result = _find_summary_thread_id(mock_requests, {}, mock_config, "repo-id", 25230)

        assert result == 99
        mock_requests.get.assert_called_once()

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    def test_falls_back_on_corrupt_review_state_json(self, temp_state_dir, clear_state_before):
        """Falls back to thread search when review-state.json is corrupt (ValueError/JSONDecodeError)."""
        import json

        from agentic_devtools.cli.azure_devops.commands import _find_summary_thread_id
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig

        mock_config = MagicMock(spec=AzureDevOpsConfig)
        mock_config.build_api_url.return_value = "https://api/threads"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": 77,
                    "comments": [{"content": "## Overall PR Review Summary\nCorrupt fallback."}],
                }
            ]
        }
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            side_effect=json.JSONDecodeError("corrupt", "", 0),
        ):
            result = _find_summary_thread_id(mock_requests, {}, mock_config, "repo-id", 25230)

        assert result == 77
        mock_requests.get.assert_called_once()

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    def test_falls_back_on_os_error_reading_review_state(self, temp_state_dir, clear_state_before):
        """Falls back to thread search when review-state.json cannot be read (OSError)."""
        from agentic_devtools.cli.azure_devops.commands import _find_summary_thread_id
        from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig

        mock_config = MagicMock(spec=AzureDevOpsConfig)
        mock_config.build_api_url.return_value = "https://api/threads"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": 88,
                    "comments": [{"content": "## Overall PR Review Summary\nOS error fallback."}],
                }
            ]
        }
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.review_state.load_review_state",
            side_effect=OSError("permission denied"),
        ):
            result = _find_summary_thread_id(mock_requests, {}, mock_config, "repo-id", 25230)

        assert result == 88
        mock_requests.get.assert_called_once()
