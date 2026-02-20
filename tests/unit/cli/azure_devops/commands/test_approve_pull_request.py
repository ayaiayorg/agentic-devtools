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
