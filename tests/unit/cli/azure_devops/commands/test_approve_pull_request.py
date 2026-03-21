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

    def test_dry_run_mentions_review_narrative(self, temp_state_dir, clear_state_before, capsys):
        """Dry-run mentions that the Review Narrative will be updated."""
        state.set_pull_request_id(12345)
        state.set_value("content", "LGTM!")
        state.set_dry_run(True)

        azure_devops.approve_pull_request()

        captured = capsys.readouterr()
        assert "Review Narrative" in captured.out

    def test_dry_run_shows_content(self, temp_state_dir, clear_state_before, capsys):
        """Dry-run output includes the approval content."""
        state.set_pull_request_id(12345)
        state.set_value("content", "All criteria met!")
        state.set_dry_run(True)

        azure_devops.approve_pull_request()

        captured = capsys.readouterr()
        assert "All criteria met!" in captured.out

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
    def test_successful_approval_via_narrative_update(
        self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before, capsys
    ):
        """Approval updates Review Narrative via patch when review state exists."""
        from agentic_devtools.cli.azure_devops.review_state import (
            FileEntry,
            OverallSummary,
            ReviewState,
        )

        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "content": "updated"}
        mock_req_module.patch.return_value = mock_response
        mock_requests.return_value = mock_req_module

        review_state = ReviewState(
            prId=12345,
            repoId="repo-guid-123",
            repoName="dfly-platform-management",
            project="DragonflyMgmt",
            organization="https://dev.azure.com/swica",
            latestIterationId=1,
            scaffoldedUtc="2026-01-01T00:00:00Z",
            overallSummary=OverallSummary(threadId=99, commentId=1),
            files={
                "/src/app.py": FileEntry(threadId=10, commentId=1, folder="src", fileName="app.py", status="approved")
            },
        )

        state.set_pull_request_id(12345)
        state.set_value("content", "LGTM! All files reviewed.")

        with patch(
            "agentic_devtools.cli.azure_devops.commands.load_review_state",
            return_value=review_state,
        ), patch("agentic_devtools.cli.azure_devops.commands.save_review_state"):
            azure_devops.approve_pull_request()

        # Should have called PATCH to update the summary comment
        assert mock_req_module.patch.called
        captured = capsys.readouterr()
        assert "Review Narrative updated successfully" in captured.out

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_approval_falls_back_when_no_review_state(
        self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before, capsys
    ):
        """Approval falls back to a new comment thread when review-state.json is missing."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 123}
        mock_req_module.post.return_value = mock_response
        mock_req_module.patch.return_value = mock_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_value("content", "LGTM!")

        with patch(
            "agentic_devtools.cli.azure_devops.commands.load_review_state",
            side_effect=FileNotFoundError("no review state"),
        ):
            azure_devops.approve_pull_request()

        # Should warn about narrative update failure and fall back to new comment
        captured = capsys.readouterr()
        assert "Could not update Review Narrative" in captured.err
        assert "Comment added successfully" in captured.out

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch(f"{COMMANDS_MODULE}.require_requests")
    @patch(f"{COMMANDS_MODULE}.get_repository_id")
    def test_approval_fallback_clears_stale_path(
        self, mock_get_repo, mock_requests, temp_state_dir, clear_state_before
    ):
        """Fallback add_pull_request_comment posts PR-level (no file context) because path is cleared."""
        mock_get_repo.return_value = "repo-guid-123"
        mock_req_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 123}
        mock_req_module.post.return_value = mock_response
        mock_req_module.patch.return_value = mock_response
        mock_requests.return_value = mock_req_module

        state.set_pull_request_id(12345)
        state.set_value("content", "LGTM!")
        # Stale path from a previous file-review operation
        state.set_value("path", "src/reviewed_file.py")
        state.set_value("line", 10)

        with patch(
            "agentic_devtools.cli.azure_devops.commands.load_review_state",
            side_effect=FileNotFoundError("no review state"),
        ):
            azure_devops.approve_pull_request()

        # The fallback thread should have no file context
        post_call = mock_req_module.post.call_args_list[-1]
        body = post_call[1]["json"]
        assert "threadContext" not in body
