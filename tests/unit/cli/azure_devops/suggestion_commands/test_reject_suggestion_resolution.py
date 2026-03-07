"""Tests for reject_suggestion_resolution CLI command."""

from unittest.mock import MagicMock, patch

import pytest


class TestRejectSuggestionResolution:
    """Tests for reject_suggestion_resolution."""

    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_repository_id", return_value="repo-id-123")
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_auth_headers", return_value={"Auth": "x"})
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_pat", return_value="fake-pat")
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.require_requests")
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.is_dry_run", return_value=False)
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_value")
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_thread_id", return_value=500)
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_pull_request_id", return_value=12345)
    def test_reactivates_thread_and_posts_reply(
        self,
        mock_pr_id,
        mock_thread_id,
        mock_get_value,
        mock_dry_run,
        mock_requests_fn,
        mock_get_pat,
        mock_get_headers,
        mock_get_repo_id,
        capsys,
    ):
        """Reject reactivates thread and posts explanation reply."""
        mock_get_value.return_value = "The null check is still missing."
        mock_requests = MagicMock()
        mock_requests_fn.return_value = mock_requests
        # POST reply
        post_response = MagicMock()
        post_response.json.return_value = {"id": 888}
        post_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = post_response
        # PATCH reactivate
        patch_response = MagicMock()
        patch_response.raise_for_status = MagicMock()
        mock_requests.patch.return_value = patch_response

        from agentic_devtools.cli.azure_devops.suggestion_commands import reject_suggestion_resolution

        reject_suggestion_resolution()

        # Verify POST was called (reply)
        mock_requests.post.assert_called_once()
        body = mock_requests.post.call_args[1]["json"]
        assert "❌ Suggestion not properly addressed" in body["content"]
        assert "null check is still missing" in body["content"]

        # Verify PATCH was called (reactivate)
        mock_requests.patch.assert_called_once()
        patch_body = mock_requests.patch.call_args[1]["json"]
        assert patch_body["status"] == "active"

        captured = capsys.readouterr()
        assert "Reply posted" in captured.out
        assert "reactivated" in captured.out

    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.is_dry_run", return_value=True)
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_value", return_value="Some explanation")
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_thread_id", return_value=500)
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_pull_request_id", return_value=12345)
    def test_dry_run_no_api_calls(self, mock_pr_id, mock_thread_id, mock_get_value, mock_dry_run, capsys):
        """Dry run prints preview without API calls."""
        from agentic_devtools.cli.azure_devops.suggestion_commands import reject_suggestion_resolution

        reject_suggestion_resolution()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "500" in captured.out

    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.require_requests")
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.is_dry_run", return_value=False)
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_value", return_value=None)
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_thread_id", return_value=500)
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_pull_request_id", return_value=12345)
    def test_missing_explanation_exits(
        self, mock_pr_id, mock_thread_id, mock_get_value, mock_dry_run, mock_requests_fn
    ):
        """Missing explanation exits with error."""
        from agentic_devtools.cli.azure_devops.suggestion_commands import reject_suggestion_resolution

        with pytest.raises(SystemExit):
            reject_suggestion_resolution()
