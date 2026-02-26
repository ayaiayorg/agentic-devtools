"""Tests for add_pull_request_comment function."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import azure_devops
from agentic_devtools.cli.azure_devops.commands import _find_summary_thread_id

# Use string paths for patching to ensure we patch the right location
COMMANDS_MODULE = "agentic_devtools.cli.azure_devops.commands"


class TestAddPullRequestComment:
    """Tests for add_pull_request_comment command."""

    def test_dry_run_basic(self, temp_state_dir, clear_state_before, capsys):
        """Test basic dry run output."""
        state.set_pull_request_id(12345)
        state.set_value("content", "Test comment")
        state.set_dry_run(True)

        azure_devops.add_pull_request_comment()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "12345" in captured.out
        assert "Test comment" in captured.out

    def test_dry_run_with_file_context(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with file context."""
        state.set_pull_request_id(12345)
        state.set_value("content", "Comment on file")
        state.set_value("path", "src/main.py")
        state.set_value("line", 42)
        state.set_dry_run(True)

        azure_devops.add_pull_request_comment()

        captured = capsys.readouterr()
        assert "src/main.py" in captured.out
        assert "42" in captured.out

    def test_dry_run_with_end_line(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with line range."""
        state.set_pull_request_id(12345)
        state.set_value("content", "Multi-line comment")
        state.set_value("path", "src/main.py")
        state.set_value("line", 10)
        state.set_value("end_line", 20)
        state.set_dry_run(True)

        azure_devops.add_pull_request_comment()

        captured = capsys.readouterr()
        assert "10" in captured.out
        assert "20" in captured.out

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before):
        """Test raises error when pull request ID is missing."""
        state.set_value("content", "Test comment")
        with pytest.raises(KeyError, match="pull_request_id"):
            azure_devops.add_pull_request_comment()

    def test_missing_content(self, temp_state_dir, clear_state_before):
        """Test exits when content is missing."""
        state.set_pull_request_id(12345)
        with pytest.raises(SystemExit):
            azure_devops.add_pull_request_comment()

    def test_approval_mode_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test approval mode shows sentinel note."""
        state.set_pull_request_id(12345)
        state.set_value("content", "LGTM!")
        state.set_value("is_pull_request_approval", True)
        state.set_dry_run(True)

        azure_devops.add_pull_request_comment()

        captured = capsys.readouterr()
        assert "approval" in captured.out.lower() or "sentinel" in captured.out.lower()

    def test_leave_thread_active_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test leave_thread_active mode shows in dry run."""
        state.set_pull_request_id(12345)
        state.set_value("content", "Keep this active")
        state.set_value("leave_thread_active", True)
        state.set_dry_run(True)

        azure_devops.add_pull_request_comment()

        captured = capsys.readouterr()
        # Should NOT mention resolving since leave_thread_active is True
        assert "Would also resolve" not in captured.out

    def test_default_resolves_thread_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test default behavior shows thread will be resolved."""
        state.set_pull_request_id(12345)
        state.set_value("content", "Will resolve")
        # leave_thread_active defaults to False
        state.set_dry_run(True)

        azure_devops.add_pull_request_comment()

        captured = capsys.readouterr()
        assert "resolve" in captured.out.lower()


class TestAddPullRequestCommentActualCall:
    """Tests for add_pull_request_comment with mocked API calls."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_successful_comment(self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before):
        """Test successful PR comment."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 123}
        mock_req_module.post.return_value = mock_response
        mock_req_module.patch.return_value = mock_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_value("content", "Test comment")

        azure_devops.add_pull_request_comment()

        mock_req_module.post.assert_called_once()
        call_args = mock_req_module.post.call_args
        assert "threads" in call_args[0][0]

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_comment_with_auto_resolve(self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before):
        """Test comment auto-resolves by default."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 123}
        mock_req_module.post.return_value = mock_response
        mock_req_module.patch.return_value = mock_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_value("content", "Will resolve")
        # leave_thread_active defaults to False

        azure_devops.add_pull_request_comment()

        # Should call patch to resolve the thread
        assert mock_req_module.patch.called

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_comment_with_file_context(self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before):
        """Test comment with file context."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 123}
        mock_req_module.post.return_value = mock_response
        mock_req_module.patch.return_value = mock_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_value("content", "File comment")
        state.set_value("path", "src/main.py")
        state.set_value("line", 42)

        azure_devops.add_pull_request_comment()

        call_args = mock_req_module.post.call_args
        body = call_args[1]["json"]
        assert "threadContext" in body
        assert body["threadContext"]["filePath"] == "src/main.py"

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_approval_comment(self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before):
        """Test approval comment includes sentinel when no summary thread exists."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {"id": 123}
        mock_req_module.post.return_value = mock_post_response
        mock_req_module.patch.return_value = mock_post_response
        # No existing summary thread
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {"value": []}
        mock_req_module.get.return_value = mock_get_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_value("content", "LGTM!")
        state.set_value("is_pull_request_approval", True)

        azure_devops.add_pull_request_comment()

        # Falls back to creating a new thread with sentinel
        post_call = mock_req_module.post.call_args_list[-1]
        body = post_call[1]["json"]
        content = body["comments"][0]["content"]
        assert azure_devops.APPROVAL_SENTINEL in content

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_file_level_approval_preserves_file_context(
        self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before
    ):
        """File-level approvals must retain file context when path and is_pull_request_approval are both set."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {"id": 123}
        mock_req_module.post.return_value = mock_post_response
        mock_req_module.patch.return_value = mock_post_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_value("content", "Approved file")
        state.set_value("is_pull_request_approval", True)
        state.set_value("path", "src/component.ts")
        state.set_value("line", 42)

        azure_devops.add_pull_request_comment()

        call_args = mock_req_module.post.call_args
        body = call_args[1]["json"]
        assert "threadContext" in body
        assert body["threadContext"]["filePath"] == "src/component.ts"

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_approve_pull_request_clears_stale_path(
        self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before
    ):
        """approve_pull_request() clears stale path so approval posts as PR-level comment or summary reply."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {"id": 123}
        mock_req_module.post.return_value = mock_post_response
        mock_req_module.patch.return_value = mock_post_response
        # No existing summary thread
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {"value": []}
        mock_req_module.get.return_value = mock_get_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_value("content", "LGTM!")
        # Simulate stale path left behind by a previous file-review operation
        state.set_value("path", "src/reviewed_file.py")
        state.set_value("line", 10)

        azure_devops.approve_pull_request()

        # Falls back to new thread; no file context because approve_pull_request clears it
        post_call = mock_req_module.post.call_args_list[-1]
        body = post_call[1]["json"]
        assert "threadContext" not in body

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_approval_replies_to_existing_summary_thread(
        self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before
    ):
        """Approval posts as reply to the existing summary thread when one exists."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {"id": 456}
        mock_req_module.post.return_value = mock_post_response
        # Existing summary thread
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {
            "value": [
                {
                    "id": 99,
                    "comments": [{"content": "## Overall PR Review Summary\n\n*Status:* Approved"}],
                }
            ]
        }
        mock_req_module.get.return_value = mock_get_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_value("content", "LGTM!")
        state.set_value("is_pull_request_approval", True)

        azure_devops.add_pull_request_comment()

        # Should reply to existing thread 99, not create a new thread
        post_call = mock_req_module.post.call_args
        url = post_call[0][0]
        assert "/threads/99/comments" in url
        body = post_call[1]["json"]
        assert azure_devops.APPROVAL_SENTINEL in body["content"]

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_approval_falls_back_when_no_summary_thread(
        self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before, capsys
    ):
        """Approval creates new thread when no summary thread exists."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {"id": 200}
        mock_req_module.post.return_value = mock_post_response
        mock_req_module.patch.return_value = mock_post_response
        # No matching summary thread
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {"value": [{"id": 50, "comments": [{"content": "Regular comment"}]}]}
        mock_req_module.get.return_value = mock_get_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_value("content", "LGTM!")
        state.set_value("is_pull_request_approval", True)

        azure_devops.add_pull_request_comment()

        captured = capsys.readouterr()
        assert "Comment added successfully" in captured.out
        # Should create a new thread endpoint (not a /comments reply endpoint)
        post_call = mock_req_module.post.call_args
        url = post_call[0][0]
        assert "/threads" in url and "/comments" not in url

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_approval_falls_back_when_summary_reply_fails(
        self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before, capsys
    ):
        """Approval creates new thread when replying to summary thread fails."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        # First POST (reply to summary) raises, second POST (new thread) succeeds
        mock_error_response = MagicMock()
        mock_error_response.raise_for_status.side_effect = Exception("Thread deleted")
        mock_ok_response = MagicMock()
        mock_ok_response.json.return_value = {"id": 300}
        mock_req_module.post.side_effect = [mock_error_response, mock_ok_response]
        mock_req_module.patch.return_value = mock_ok_response
        # Summary thread exists
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {
            "value": [{"id": 99, "comments": [{"content": "## Overall PR Review Summary\nApproved"}]}]
        }
        mock_req_module.get.return_value = mock_get_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_value("content", "LGTM!")
        state.set_value("is_pull_request_approval", True)

        azure_devops.add_pull_request_comment()

        captured = capsys.readouterr()
        # Should warn that replying to the summary thread failed
        assert "could not reply to summary thread" in captured.err.lower()
        # Should fall back to creating a new thread
        assert "Comment added successfully" in captured.out

    def test_approve_pull_request_dry_run_clears_stale_path(self, temp_state_dir, clear_state_before, capsys):
        """approve_pull_request() dry-run must not mention file path even when path state was set."""
        state.set_pull_request_id(12345)
        state.set_value("content", "LGTM!")
        state.set_value("path", "src/reviewed_file.py")
        state.set_dry_run(True)

        azure_devops.approve_pull_request()

        captured = capsys.readouterr()
        assert "src/reviewed_file.py" not in captured.out

    def test_approval_dry_run_mentions_summary_thread(self, temp_state_dir, clear_state_before, capsys):
        """Dry-run approval mentions it will try to reply to summary thread."""
        state.set_pull_request_id(12345)
        state.set_value("content", "LGTM!")
        state.set_value("is_pull_request_approval", True)
        state.set_dry_run(True)

        azure_devops.add_pull_request_comment()

        captured = capsys.readouterr()
        assert "summary thread" in captured.out.lower()


class TestFindSummaryThreadId:
    """Tests for _find_summary_thread_id helper."""

    def test_returns_thread_id_when_summary_exists(self):
        """Returns the thread ID when an 'Overall PR Review Summary' thread is found."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {"id": 10, "comments": [{"content": "Some other thread"}]},
                {
                    "id": 42,
                    "comments": [{"content": "## Overall PR Review Summary\n\n*Status:* Approved"}],
                },
            ]
        }
        mock_requests.get.return_value = mock_response
        config = MagicMock()
        config.build_api_url.return_value = "https://example.com/threads"

        result = _find_summary_thread_id(mock_requests, {}, config, "repo-id", 123)
        assert result == 42

    def test_returns_none_when_no_summary_thread(self):
        """Returns None when no summary thread exists."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": [{"id": 10, "comments": [{"content": "Not a summary"}]}]}
        mock_requests.get.return_value = mock_response
        config = MagicMock()
        config.build_api_url.return_value = "https://example.com/threads"

        result = _find_summary_thread_id(mock_requests, {}, config, "repo-id", 123)
        assert result is None

    def test_returns_none_when_no_threads(self):
        """Returns None when there are no threads at all."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_requests.get.return_value = mock_response
        config = MagicMock()
        config.build_api_url.return_value = "https://example.com/threads"

        result = _find_summary_thread_id(mock_requests, {}, config, "repo-id", 123)
        assert result is None

    def test_returns_none_on_api_error(self):
        """Returns None when the API call fails."""
        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("Network error")
        config = MagicMock()
        config.build_api_url.return_value = "https://example.com/threads"

        result = _find_summary_thread_id(mock_requests, {}, config, "repo-id", 123)
        assert result is None

    def test_warns_and_returns_none_when_thread_has_no_id(self, capsys):
        """Returns None and logs warning when summary thread has no 'id' field."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {
                    "comments": [{"content": "## Overall PR Review Summary\n\n*Status:* Approved"}],
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        config = MagicMock()
        config.build_api_url.return_value = "https://example.com/threads"

        result = _find_summary_thread_id(mock_requests, {}, config, "repo-id", 123)
        assert result is None
        captured = capsys.readouterr()
        assert "without an 'id' field" in captured.err
