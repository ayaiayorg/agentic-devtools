"""Tests for reply_to_pull_request_thread function."""
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import azure_devops

# Use string paths for patching to ensure we patch the right location
COMMANDS_MODULE = "agentic_devtools.cli.azure_devops.commands"

class TestReplyToPullRequestThread:
    """Tests for reply_to_pull_request_thread command."""

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output shows correct information."""
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_value("content", "Test reply")
        state.set_dry_run(True)

        azure_devops.reply_to_pull_request_thread()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "12345" in captured.out
        assert "67890" in captured.out
        assert "Test reply" in captured.out

    def test_dry_run_with_resolve(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows resolve intent."""
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_value("content", "Test reply")
        state.set_value("resolve_thread", True)
        state.set_dry_run(True)

        azure_devops.reply_to_pull_request_thread()

        captured = capsys.readouterr()
        assert "resolve" in captured.out.lower()

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before):
        """Test raises error when pull request ID is missing."""
        state.set_thread_id(67890)
        state.set_value("content", "Test reply")
        with pytest.raises(KeyError, match="pull_request_id"):
            azure_devops.reply_to_pull_request_thread()

    def test_missing_thread_id(self, temp_state_dir, clear_state_before):
        """Test raises error when thread ID is missing."""
        state.set_pull_request_id(12345)
        state.set_value("content", "Test reply")
        with pytest.raises(KeyError, match="thread_id"):
            azure_devops.reply_to_pull_request_thread()

    def test_missing_content(self, temp_state_dir, clear_state_before):
        """Test exits when content is missing."""
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        with pytest.raises(SystemExit):
            azure_devops.reply_to_pull_request_thread()

    def test_multiline_content(self, temp_state_dir, clear_state_before, capsys):
        """Test handles multiline content."""
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_value("content", "Line 1\nLine 2\nLine 3")
        state.set_dry_run(True)

        azure_devops.reply_to_pull_request_thread()

        captured = capsys.readouterr()
        assert "Line 1" in captured.out
        assert "Line 2" in captured.out

    def test_special_characters_in_content(self, temp_state_dir, clear_state_before, capsys):
        """Test handles special characters."""
        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_value("content", "Test with \"quotes\" and 'apostrophes' and $Special$ chars!")
        state.set_dry_run(True)

        azure_devops.reply_to_pull_request_thread()

        captured = capsys.readouterr()
        assert "quotes" in captured.out

class TestReplyToPullRequestThreadActualCall:
    """Tests for reply_to_pull_request_thread with mocked API calls."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_successful_reply(self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before):
        """Test successful reply to thread."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 999}
        mock_req_module.post.return_value = mock_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_value("content", "Test reply")

        azure_devops.reply_to_pull_request_thread()

        mock_req_module.post.assert_called_once()
        call_args = mock_req_module.post.call_args
        assert "comments" in call_args[0][0]
        assert call_args[1]["json"]["content"] == "Test reply"

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_reply_with_resolve(self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before):
        """Test reply and resolve thread."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 999}
        mock_req_module.post.return_value = mock_response
        mock_req_module.patch.return_value = mock_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_thread_id(67890)
        state.set_value("content", "Fixed!")
        state.set_value("resolve_thread", True)

        azure_devops.reply_to_pull_request_thread()

        # Should have both post (comment) and patch (resolve) calls
        assert mock_req_module.post.called
        assert mock_req_module.patch.called
