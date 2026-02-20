"""Tests for add_pull_request_comment function."""
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import azure_devops

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
        """Test approval comment includes sentinel."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 123}
        mock_req_module.post.return_value = mock_response
        mock_req_module.patch.return_value = mock_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_value("content", "LGTM!")
        state.set_value("is_pull_request_approval", True)

        azure_devops.add_pull_request_comment()

        call_args = mock_req_module.post.call_args
        body = call_args[1]["json"]
        content = body["comments"][0]["content"]
        assert azure_devops.APPROVAL_SENTINEL in content
