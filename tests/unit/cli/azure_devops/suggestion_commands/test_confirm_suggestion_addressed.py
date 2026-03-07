"""Tests for confirm_suggestion_addressed CLI command."""

from unittest.mock import MagicMock, patch

import pytest


class TestConfirmSuggestionAddressed:
    """Tests for confirm_suggestion_addressed."""

    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_repository_id", return_value="repo-id-123")
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_auth_headers", return_value={"Auth": "x"})
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_pat", return_value="fake-pat")
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.require_requests")
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.is_dry_run", return_value=False)
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_value")
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_thread_id", return_value=500)
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_pull_request_id", return_value=12345)
    def test_resolves_thread_and_posts_reply(
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
        """Confirm posts reply and resolves thread."""
        mock_get_value.return_value = "abc1234567"
        mock_requests = MagicMock()
        mock_requests_fn.return_value = mock_requests
        # POST reply
        post_response = MagicMock()
        post_response.json.return_value = {"id": 999}
        post_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = post_response
        # PATCH resolve
        patch_response = MagicMock()
        patch_response.raise_for_status = MagicMock()
        mock_requests.patch.return_value = patch_response

        from agentic_devtools.cli.azure_devops.suggestion_commands import confirm_suggestion_addressed

        confirm_suggestion_addressed()

        # Verify POST was called (reply)
        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        assert "comments" in call_args[0][0]  # URL contains /comments
        body = call_args[1]["json"]
        assert "✅ Suggestion addressed" in body["content"]
        assert "abc1234" in body["content"]  # short hash

        # Verify PATCH was called (resolve thread)
        mock_requests.patch.assert_called_once()
        patch_body = mock_requests.patch.call_args[1]["json"]
        assert patch_body["status"] == "closed"

        captured = capsys.readouterr()
        assert "Reply posted" in captured.out
        assert "resolved" in captured.out

    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.is_dry_run", return_value=True)
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_value", return_value="abc1234")
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_thread_id", return_value=500)
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_pull_request_id", return_value=12345)
    def test_dry_run_no_api_calls(self, mock_pr_id, mock_thread_id, mock_get_value, mock_dry_run, capsys):
        """Dry run prints preview without API calls."""
        from agentic_devtools.cli.azure_devops.suggestion_commands import confirm_suggestion_addressed

        confirm_suggestion_addressed()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "500" in captured.out

    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.require_requests")
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.is_dry_run", return_value=False)
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_value", return_value=None)
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_thread_id", return_value=500)
    @patch("agentic_devtools.cli.azure_devops.suggestion_commands.get_pull_request_id", return_value=12345)
    def test_missing_commit_hash_exits(
        self, mock_pr_id, mock_thread_id, mock_get_value, mock_dry_run, mock_requests_fn
    ):
        """Missing commit hash exits with error."""
        from agentic_devtools.cli.azure_devops.suggestion_commands import confirm_suggestion_addressed

        with pytest.raises(SystemExit):
            confirm_suggestion_addressed()
