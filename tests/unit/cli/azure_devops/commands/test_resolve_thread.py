"""Tests for resolve_thread function."""
from agentic_devtools import state
from agentic_devtools.cli import azure_devops
from unittest.mock import MagicMock, patch
import pytest

# Use string paths for patching to ensure we patch the right location
COMMANDS_MODULE = "agentic_devtools.cli.azure_devops.commands"

class TestResolveThread:
    """Tests for resolve_thread command."""

    def test_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output."""
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_dry_run(True)

        azure_devops.resolve_thread()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "67890" in captured.out
        assert "12345" in captured.out

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before):
        """Test raises error when pull request ID is missing."""
        state.set_thread_id(67890)
        with pytest.raises(KeyError, match="pull_request_id"):
            azure_devops.resolve_thread()

    def test_missing_thread_id(self, temp_state_dir, clear_state_before):
        """Test raises error when thread ID is missing."""
        state.set_pull_request_id(12345)
        with pytest.raises(KeyError, match="thread_id"):
            azure_devops.resolve_thread()

class TestResolveThreadActualCall:
    """Tests for resolve_thread with mocked API calls."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_successful_resolve(self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before):
        """Test successful thread resolution."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_response = MagicMock()
        mock_req_module.patch.return_value = mock_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_thread_id(67890)

        azure_devops.resolve_thread()

        mock_req_module.patch.assert_called_once()
        call_args = mock_req_module.patch.call_args
        assert call_args[1]["json"]["status"] == "closed"
