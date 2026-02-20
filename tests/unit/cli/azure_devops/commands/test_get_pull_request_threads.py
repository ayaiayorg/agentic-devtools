"""Tests for get_pull_request_threads function."""
from agentic_devtools import state
from agentic_devtools.cli import azure_devops
from unittest.mock import MagicMock, patch
import pytest

# Use string paths for patching to ensure we patch the right location
COMMANDS_MODULE = "agentic_devtools.cli.azure_devops.commands"

class TestGetPullRequestThreads:
    """Tests for get_pull_request_threads command."""

    def test_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output."""
        state.set_pull_request_id(12345)
        state.set_dry_run(True)

        azure_devops.get_pull_request_threads()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "12345" in captured.out

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before):
        """Test raises error when pull request ID is missing."""
        with pytest.raises(KeyError, match="pull_request_id"):
            azure_devops.get_pull_request_threads()

class TestGetPullRequestThreadsActualCall:
    """Tests for get_pull_request_threads with mocked API calls."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_successful_get_threads(self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before, capsys):
        """Test successful thread fetch."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "id": 123,
                    "status": "active",
                    "threadContext": {},
                    "comments": [
                        {
                            "id": 1,
                            "author": {"displayName": "Test"},
                            "content": "Comment",
                        }
                    ],
                }
            ]
        }
        mock_req_module.get.return_value = mock_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)

        azure_devops.get_pull_request_threads()

        mock_req_module.get.assert_called_once()
        captured = capsys.readouterr()
        assert "123" in captured.out

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_no_threads_found(self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before, capsys):
        """Test no threads message."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_req_module.get.return_value = mock_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)

        azure_devops.get_pull_request_threads()

        captured = capsys.readouterr()
        assert "No comment threads" in captured.out
