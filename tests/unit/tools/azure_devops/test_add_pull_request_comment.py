"""Tests for agentic_devtools.tools.azure_devops.add_pull_request_comment."""

from unittest.mock import MagicMock, patch

from agentic_devtools.tools.azure_devops import add_pull_request_comment


class TestAddPullRequestComment:
    """Tests for the add_pull_request_comment tool function."""

    def _make_config(self):
        config = MagicMock()
        config.organization = "https://dev.azure.com/myorg"
        config.project = "MyProject"
        config.repository = "my-repo"
        config.build_api_url.return_value = (
            "https://dev.azure.com/myorg/_apis/git/repositories/repo-id/pullRequests/1/threads"
        )
        return config

    @patch("agentic_devtools.cli.azure_devops.helpers.resolve_thread_by_id")
    @patch("agentic_devtools.cli.azure_devops.helpers.build_thread_context", return_value=None)
    @patch("agentic_devtools.cli.azure_devops.helpers.get_repository_id", return_value="repo-id")
    @patch("agentic_devtools.cli.azure_devops.auth.get_auth_headers", return_value={"Authorization": "Basic xxx"})
    @patch("agentic_devtools.tools.azure_devops._get_requests")
    def test_returns_thread_and_comment_id(self, mock_req, mock_auth, mock_repo_id, mock_ctx, mock_resolve):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 100,
            "comments": [{"id": 200}],
        }
        mock_requests.post.return_value = mock_response
        mock_req.return_value = mock_requests
        config = self._make_config()

        result = add_pull_request_comment(
            config=config,
            pat="test-pat",
            pull_request_id=1,
            content="Great work!",
        )

        assert result["thread_id"] == 100
        assert result["comment_id"] == 200
        mock_resolve.assert_called_once()  # resolve_after_posting defaults True

    @patch("agentic_devtools.cli.azure_devops.helpers.resolve_thread_by_id")
    @patch("agentic_devtools.cli.azure_devops.helpers.build_thread_context", return_value=None)
    @patch("agentic_devtools.cli.azure_devops.helpers.get_repository_id", return_value="repo-id")
    @patch("agentic_devtools.cli.azure_devops.auth.get_auth_headers", return_value={"Authorization": "Basic xxx"})
    @patch("agentic_devtools.tools.azure_devops._get_requests")
    def test_no_resolve_when_disabled(self, mock_req, mock_auth, mock_repo_id, mock_ctx, mock_resolve):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 100, "comments": [{"id": 200}]}
        mock_requests.post.return_value = mock_response
        mock_req.return_value = mock_requests
        config = self._make_config()

        add_pull_request_comment(
            config=config,
            pat="test-pat",
            pull_request_id=1,
            content="Comment",
            resolve_after_posting=False,
        )

        mock_resolve.assert_not_called()

    @patch("agentic_devtools.cli.azure_devops.helpers.resolve_thread_by_id")
    @patch("agentic_devtools.cli.azure_devops.helpers.build_thread_context")
    @patch("agentic_devtools.cli.azure_devops.helpers.get_repository_id", return_value="repo-id")
    @patch("agentic_devtools.cli.azure_devops.auth.get_auth_headers", return_value={"Authorization": "Basic xxx"})
    @patch("agentic_devtools.tools.azure_devops._get_requests")
    def test_includes_thread_context_for_file_comment(self, mock_req, mock_auth, mock_repo_id, mock_ctx, mock_resolve):
        mock_ctx.return_value = {"filePath": "/src/main.py", "rightFileStart": {"line": 10}}
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 101, "comments": [{"id": 201}]}
        mock_requests.post.return_value = mock_response
        mock_req.return_value = mock_requests
        config = self._make_config()

        add_pull_request_comment(
            config=config,
            pat="test-pat",
            pull_request_id=1,
            content="File comment",
            path="/src/main.py",
            line=10,
        )

        call_kwargs = mock_requests.post.call_args[1]
        assert "threadContext" in call_kwargs["json"]

    @patch("agentic_devtools.cli.azure_devops.helpers.resolve_thread_by_id")
    @patch("agentic_devtools.cli.azure_devops.helpers.build_thread_context", return_value=None)
    @patch("agentic_devtools.cli.azure_devops.helpers.get_repository_id", return_value="repo-id")
    @patch("agentic_devtools.cli.azure_devops.auth.get_auth_headers", return_value={"Authorization": "Basic xxx"})
    @patch("agentic_devtools.tools.azure_devops._get_requests")
    def test_handles_empty_comments_list(self, mock_req, mock_auth, mock_repo_id, mock_ctx, mock_resolve):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 102, "comments": []}
        mock_requests.post.return_value = mock_response
        mock_req.return_value = mock_requests
        config = self._make_config()

        result = add_pull_request_comment(
            config=config,
            pat="test-pat",
            pull_request_id=1,
            content="Comment",
        )

        assert result["comment_id"] == 0

    @patch("agentic_devtools.tools.azure_devops.sys")
    @patch("agentic_devtools.cli.azure_devops.helpers.resolve_thread_by_id")
    @patch("agentic_devtools.cli.azure_devops.helpers.build_thread_context", return_value=None)
    @patch("agentic_devtools.cli.azure_devops.helpers.get_repository_id", return_value="repo-id")
    @patch("agentic_devtools.cli.azure_devops.auth.get_auth_headers", return_value={"Authorization": "Basic xxx"})
    @patch("agentic_devtools.tools.azure_devops._get_requests")
    def test_escapes_config_args_for_get_repository_id_on_windows(
        self, mock_req, mock_auth, mock_repo_id, mock_ctx, mock_resolve, mock_sys
    ):
        """Config-derived values are escaped before passing to get_repository_id on Windows."""
        mock_sys.platform = "win32"
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 100, "comments": [{"id": 200}]}
        mock_requests.post.return_value = mock_response
        mock_req.return_value = mock_requests
        config = self._make_config()
        config.organization = "https://dev.azure.com/%ORG%"
        config.project = "%PROJECT%"
        config.repository = "%REPO%"

        add_pull_request_comment(config=config, pat="pat", pull_request_id=1, content="Comment")

        mock_repo_id.assert_called_once_with("https://dev.azure.com/%%ORG%%", "%%PROJECT%%", "%%REPO%%")
