"""
Tests for Azure DevOps CLI commands with mocked API calls.
"""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import azure_devops

# Use string paths for patching to ensure we patch the right location
COMMANDS_MODULE = "agentic_devtools.cli.azure_devops.commands"


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


class TestCreatePullRequestActualCall:
    """Tests for create_pull_request with mocked subprocess calls."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_successful_pr_creation(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test successful PR creation."""
        # Mock az --version check
        mock_version = MagicMock()
        mock_version.returncode = 0

        # Mock extension check
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"

        # Mock pr create
        mock_create = MagicMock()
        mock_create.returncode = 0
        mock_create.stdout = '{"pullRequestId": 999, "repository": {"webUrl": "https://test"}}'

        mock_run.side_effect = [mock_version, mock_ext, mock_create]

        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "999" in captured.out

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_pr_creation_failure(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test PR creation fails when az command fails."""
        # Mock az --version check
        mock_version = MagicMock()
        mock_version.returncode = 0

        # Mock extension check
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"

        # Mock pr create failure
        mock_create = MagicMock()
        mock_create.returncode = 1
        mock_create.stderr = "PR creation failed: branch not found"

        mock_run.side_effect = [mock_version, mock_ext, mock_create]

        state.set_value("source_branch", "feature/nonexistent")
        state.set_value("title", "Test PR")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.create_pull_request()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error creating PR" in captured.err

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_pr_creation_with_description(self, mock_run, temp_state_dir, clear_state_before):
        """Test PR creation with description."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_create = MagicMock()
        mock_create.returncode = 0
        mock_create.stdout = '{"pullRequestId": 999, "repository": {}}'

        mock_run.side_effect = [mock_version, mock_ext, mock_create]

        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("description", "PR description")

        azure_devops.create_pull_request()

        # Check that description was in the command
        create_call = mock_run.call_args_list[2]
        cmd = create_call[0][0]
        assert "--description" in cmd


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


class TestMarkPullRequestDraftActualCall:
    """Tests for mark_pull_request_draft with mocked API calls."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_successful_mark_draft(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test successful mark as draft."""
        # Mock az --version check
        mock_version = MagicMock()
        mock_version.returncode = 0

        # Mock extension check
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"

        # Mock pr update
        mock_update = MagicMock()
        mock_update.returncode = 0
        mock_update.stdout = '{"pullRequestId": 12345, "isDraft": true, "repository": {"webUrl": "https://test"}}'

        mock_run.side_effect = [mock_version, mock_ext, mock_update]

        state.set_pull_request_id(12345)

        azure_devops.mark_pull_request_draft()

        captured = capsys.readouterr()
        assert "12345" in captured.out
        assert "draft" in captured.out.lower()

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_mark_draft_includes_draft_flag(self, mock_run, temp_state_dir, clear_state_before):
        """Test that mark_pull_request_draft passes --draft true to az CLI."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_update = MagicMock()
        mock_update.returncode = 0
        mock_update.stdout = '{"pullRequestId": 12345, "repository": {}}'

        mock_run.side_effect = [mock_version, mock_ext, mock_update]

        state.set_pull_request_id(12345)

        azure_devops.mark_pull_request_draft()

        # Check that --draft true was in the command
        update_call = mock_run.call_args_list[2]
        cmd = update_call[0][0]
        assert "--draft" in cmd
        draft_idx = cmd.index("--draft")
        assert cmd[draft_idx + 1] == "true"

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_mark_draft_failure(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test mark draft fails when az command fails."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_update = MagicMock()
        mock_update.returncode = 1
        mock_update.stderr = "Failed to update PR"

        mock_run.side_effect = [mock_version, mock_ext, mock_update]

        state.set_pull_request_id(12345)

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.mark_pull_request_draft()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error marking PR as draft" in captured.err


class TestPublishPullRequestActualCall:
    """Tests for publish_pull_request with mocked API calls."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_successful_publish(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test successful publish PR."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"

        # Mock publish (draft false)
        mock_publish = MagicMock()
        mock_publish.returncode = 0
        mock_publish.stdout = '{"pullRequestId": 12345, "isDraft": false, "repository": {"webUrl": "https://test"}}'

        # Mock auto-complete
        mock_auto = MagicMock()
        mock_auto.returncode = 0
        mock_auto.stdout = '{"pullRequestId": 12345}'

        mock_run.side_effect = [mock_version, mock_ext, mock_publish, mock_auto]

        state.set_pull_request_id(12345)

        azure_devops.publish_pull_request()

        captured = capsys.readouterr()
        assert "published" in captured.out.lower()
        assert "Auto-complete enabled" in captured.out

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_publish_with_skip_auto_complete(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test publish PR with skip auto-complete."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_publish = MagicMock()
        mock_publish.returncode = 0
        mock_publish.stdout = '{"pullRequestId": 12345, "repository": {"webUrl": "https://test"}}'

        mock_run.side_effect = [mock_version, mock_ext, mock_publish]

        state.set_pull_request_id(12345)
        state.set_value("skip_auto_complete", True)

        azure_devops.publish_pull_request()

        captured = capsys.readouterr()
        assert "published" in captured.out.lower()
        assert "Auto-complete enabled" not in captured.out

        # Check that auto-complete call was NOT made (only 3 subprocess calls)
        assert mock_run.call_count == 3

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_publish_includes_draft_false(self, mock_run, temp_state_dir, clear_state_before):
        """Test that publish_pull_request passes --draft false to az CLI."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_publish = MagicMock()
        mock_publish.returncode = 0
        mock_publish.stdout = '{"pullRequestId": 12345, "repository": {}}'
        mock_auto = MagicMock()
        mock_auto.returncode = 0
        mock_auto.stdout = "{}"

        mock_run.side_effect = [mock_version, mock_ext, mock_publish, mock_auto]

        state.set_pull_request_id(12345)

        azure_devops.publish_pull_request()

        # Check that --draft false was in the publish command
        publish_call = mock_run.call_args_list[2]
        cmd = publish_call[0][0]
        assert "--draft" in cmd
        draft_idx = cmd.index("--draft")
        assert cmd[draft_idx + 1] == "false"

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_publish_includes_auto_complete_true(self, mock_run, temp_state_dir, clear_state_before):
        """Test that publish_pull_request passes --auto-complete true to az CLI."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_publish = MagicMock()
        mock_publish.returncode = 0
        mock_publish.stdout = '{"pullRequestId": 12345, "repository": {}}'
        mock_auto = MagicMock()
        mock_auto.returncode = 0
        mock_auto.stdout = "{}"

        mock_run.side_effect = [mock_version, mock_ext, mock_publish, mock_auto]

        state.set_pull_request_id(12345)

        azure_devops.publish_pull_request()

        # Check that --auto-complete true was in the auto-complete command
        auto_call = mock_run.call_args_list[3]
        cmd = auto_call[0][0]
        assert "--auto-complete" in cmd
        auto_idx = cmd.index("--auto-complete")
        assert cmd[auto_idx + 1] == "true"

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_publish_failure(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test publish fails when az command fails."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_publish = MagicMock()
        mock_publish.returncode = 1
        mock_publish.stderr = "Failed to publish PR"

        mock_run.side_effect = [mock_version, mock_ext, mock_publish]

        state.set_pull_request_id(12345)

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.publish_pull_request()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error publishing PR" in captured.err

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_auto_complete_failure_is_warning(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test auto-complete failure is a warning, not fatal."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_publish = MagicMock()
        mock_publish.returncode = 0
        mock_publish.stdout = '{"pullRequestId": 12345, "repository": {"webUrl": "https://test"}}'
        mock_auto = MagicMock()
        mock_auto.returncode = 1
        mock_auto.stderr = "Auto-complete failed"

        mock_run.side_effect = [mock_version, mock_ext, mock_publish, mock_auto]

        state.set_pull_request_id(12345)

        # Should not raise, just print warning
        azure_devops.publish_pull_request()

        captured = capsys.readouterr()
        assert "published" in captured.out.lower()
        assert "Warning" in captured.err
        assert "Auto-complete enabled" not in captured.out


class TestRunE2eTestsSynapseActualCall:
    """Tests for run_e2e_tests_synapse with mocked API calls."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_successful_queue(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test successful pipeline queue."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_queue = MagicMock()
        mock_queue.returncode = 0
        mock_queue.stdout = '{"id": 99999, "_links": {"web": {"href": "https://test/logs"}}}'

        mock_run.side_effect = [mock_version, mock_ext, mock_queue]

        state.set_value("branch", "feature/test")

        azure_devops.run_e2e_tests_synapse()

        captured = capsys.readouterr()
        assert "queued successfully" in captured.out.lower()
        assert "99999" in captured.out

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_queue_includes_stage_param(self, mock_run, temp_state_dir, clear_state_before):
        """Test that run_e2e_tests_synapse passes stage parameter."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_queue = MagicMock()
        mock_queue.returncode = 0
        mock_queue.stdout = '{"id": 99999}'

        mock_run.side_effect = [mock_version, mock_ext, mock_queue]

        state.set_value("branch", "feature/test")
        state.set_value("e2e.stage", "INT")

        azure_devops.run_e2e_tests_synapse()

        # Check that --parameters stage=INT was in the command
        queue_call = mock_run.call_args_list[2]
        cmd = queue_call[0][0]
        assert "--parameters" in cmd
        assert "stage=INT" in cmd

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_queue_failure(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test queue fails when az command fails."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_queue = MagicMock()
        mock_queue.returncode = 1
        mock_queue.stderr = "Failed to queue pipeline"

        mock_run.side_effect = [mock_version, mock_ext, mock_queue]

        state.set_value("branch", "feature/test")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.run_e2e_tests_synapse()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error queuing pipeline" in captured.err


class TestRunE2eTestsFabricActualCall:
    """Tests for run_e2e_tests_fabric with mocked API calls."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_successful_queue(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test successful pipeline queue."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_queue = MagicMock()
        mock_queue.returncode = 0
        mock_queue.stdout = '{"id": 88888, "_links": {"web": {"href": "https://test/logs"}}}'

        mock_run.side_effect = [mock_version, mock_ext, mock_queue]

        state.set_value("branch", "feature/test")

        azure_devops.run_e2e_tests_fabric()

        captured = capsys.readouterr()
        assert "queued successfully" in captured.out.lower()
        assert "88888" in captured.out

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_queue_uses_fabric_pipeline(self, mock_run, temp_state_dir, clear_state_before):
        """Test that run_e2e_tests_fabric uses the correct pipeline name."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_queue = MagicMock()
        mock_queue.returncode = 0
        mock_queue.stdout = '{"id": 88888}'

        mock_run.side_effect = [mock_version, mock_ext, mock_queue]

        state.set_value("branch", "feature/test")

        azure_devops.run_e2e_tests_fabric()

        # Check that the pipeline name is mgmt-e2e-tests-fabric
        queue_call = mock_run.call_args_list[2]
        cmd = queue_call[0][0]
        assert "mgmt-e2e-tests-fabric" in cmd

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_queue_failure(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test queue fails when az command fails."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_queue = MagicMock()
        mock_queue.returncode = 1
        mock_queue.stderr = "Failed to queue pipeline"

        mock_run.side_effect = [mock_version, mock_ext, mock_queue]

        state.set_value("branch", "feature/test")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.run_e2e_tests_fabric()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error queuing pipeline" in captured.err


class TestRunWbPatchActualCall:
    """Tests for run_wb_patch with mocked API calls."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_successful_queue(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test successful pipeline queue."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_queue = MagicMock()
        mock_queue.returncode = 0
        mock_queue.stdout = '{"id": 88888, "_links": {"web": {"href": "https://test/logs"}}}'

        mock_run.side_effect = [mock_version, mock_ext, mock_queue]

        state.set_value("branch", "feature/test")
        state.set_value("wb_patch.workbench", "STND")

        azure_devops.run_wb_patch()

        captured = capsys.readouterr()
        assert "queued successfully" in captured.out.lower()
        assert "88888" in captured.out

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_queue_includes_workbench_param(self, mock_run, temp_state_dir, clear_state_before):
        """Test that run_wb_patch passes workbench parameter."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_queue = MagicMock()
        mock_queue.returncode = 0
        mock_queue.stdout = '{"id": 88888}'

        mock_run.side_effect = [mock_version, mock_ext, mock_queue]

        state.set_value("branch", "feature/test")
        state.set_value("wb_patch.workbench", "TESR")

        azure_devops.run_wb_patch()

        # Check that workbench=TESR was in the command
        queue_call = mock_run.call_args_list[2]
        cmd = queue_call[0][0]
        assert "workbench=TESR" in cmd

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_queue_includes_all_params(self, mock_run, temp_state_dir, clear_state_before):
        """Test that run_wb_patch passes all parameters."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_queue = MagicMock()
        mock_queue.returncode = 0
        mock_queue.stdout = '{"id": 88888}'

        mock_run.side_effect = [mock_version, mock_ext, mock_queue]

        state.set_value("branch", "feature/test")
        state.set_value("wb_patch.workbench", "STND")
        state.set_value("wb_patch.helper_lib_version", "2.0.0")
        state.set_value("wb_patch.plan_only", "false")
        state.set_value("wb_patch.deploy_helper_lib", "true")

        azure_devops.run_wb_patch()

        queue_call = mock_run.call_args_list[2]
        cmd = queue_call[0][0]
        assert "workbench=STND" in cmd
        assert "helper_lib_version=2.0.0" in cmd
        assert "plan_only=false" in cmd
        assert "deploy_helper_lib=true" in cmd

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_queue_failure(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test queue fails when az command fails."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_queue = MagicMock()
        mock_queue.returncode = 1
        mock_queue.stderr = "Failed to queue pipeline"

        mock_run.side_effect = [mock_version, mock_ext, mock_queue]

        state.set_value("branch", "feature/test")
        state.set_value("wb_patch.workbench", "STND")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.run_wb_patch()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error queuing pipeline" in captured.err
