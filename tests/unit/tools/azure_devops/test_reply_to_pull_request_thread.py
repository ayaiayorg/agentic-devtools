"""Tests for agentic_devtools.tools.azure_devops.reply_to_pull_request_thread."""

from unittest.mock import MagicMock, patch

from agentic_devtools.tools.azure_devops import reply_to_pull_request_thread


class TestReplyToPullRequestThread:
    """Tests for the reply_to_pull_request_thread tool function."""

    def _make_config(self):
        config = MagicMock()
        config.organization = "https://dev.azure.com/myorg"
        config.project = "MyProject"
        config.repository = "my-repo"
        config.build_api_url.return_value = (
            "https://dev.azure.com/myorg/_apis/git/repositories/repo-id/pullRequests/1/threads/10/comments"
        )
        return config

    @patch("agentic_devtools.cli.azure_devops.helpers.resolve_thread_by_id")
    @patch("agentic_devtools.cli.azure_devops.helpers.get_repository_id", return_value="repo-id")
    @patch("agentic_devtools.cli.azure_devops.auth.get_auth_headers", return_value={"Authorization": "Basic xxx"})
    @patch("agentic_devtools.tools.azure_devops._get_requests")
    def test_returns_comment_id(self, mock_req, mock_auth, mock_repo_id, mock_resolve):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 42}
        mock_requests.post.return_value = mock_response
        mock_req.return_value = mock_requests
        config = self._make_config()

        result = reply_to_pull_request_thread(
            config=config,
            pat="test-pat",
            pull_request_id=1,
            thread_id=10,
            content="Thanks!",
        )

        assert result["comment_id"] == 42
        assert result["thread_resolved"] is False
        mock_resolve.assert_not_called()

    @patch("agentic_devtools.cli.azure_devops.helpers.resolve_thread_by_id")
    @patch("agentic_devtools.cli.azure_devops.helpers.get_repository_id", return_value="repo-id")
    @patch("agentic_devtools.cli.azure_devops.auth.get_auth_headers", return_value={"Authorization": "Basic xxx"})
    @patch("agentic_devtools.tools.azure_devops._get_requests")
    def test_resolves_thread_when_requested(self, mock_req, mock_auth, mock_repo_id, mock_resolve):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 42}
        mock_requests.post.return_value = mock_response
        mock_req.return_value = mock_requests
        config = self._make_config()

        result = reply_to_pull_request_thread(
            config=config,
            pat="test-pat",
            pull_request_id=1,
            thread_id=10,
            content="Fixed, resolving.",
            resolve_thread=True,
        )

        assert result["thread_resolved"] is True
        mock_resolve.assert_called_once()

    @patch("agentic_devtools.tools.azure_devops.sys")
    @patch("agentic_devtools.cli.azure_devops.helpers.resolve_thread_by_id")
    @patch("agentic_devtools.cli.azure_devops.helpers.get_repository_id", return_value="repo-id")
    @patch("agentic_devtools.cli.azure_devops.auth.get_auth_headers", return_value={"Authorization": "Basic xxx"})
    @patch("agentic_devtools.tools.azure_devops._get_requests")
    def test_escapes_config_args_for_get_repository_id_on_windows(
        self, mock_req, mock_auth, mock_repo_id, mock_resolve, mock_sys
    ):
        """Config-derived values are escaped before passing to get_repository_id on Windows."""
        mock_sys.platform = "win32"
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 42}
        mock_requests.post.return_value = mock_response
        mock_req.return_value = mock_requests
        config = self._make_config()
        config.organization = "https://dev.azure.com/%ORG%"
        config.project = "%PROJECT%"
        config.repository = "%REPO%"

        reply_to_pull_request_thread(config=config, pat="pat", pull_request_id=1, thread_id=10, content="Hi")

        mock_repo_id.assert_called_once_with("https://dev.azure.com/%%ORG%%", "%%PROJECT%%", "%%REPO%%")
