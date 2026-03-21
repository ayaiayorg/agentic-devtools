"""Tests for agentic_devtools.tools.azure_devops.create_pull_request."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.tools.azure_devops import create_pull_request


class TestCreatePullRequest:
    """Tests for the create_pull_request tool function."""

    def _make_config(self):
        config = MagicMock()
        config.organization = "https://dev.azure.com/myorg"
        config.project = "MyProject"
        config.repository = "my-repo"
        return config

    @patch("agentic_devtools.cli.subprocess_utils.run_safe")
    @patch("agentic_devtools.cli.azure_devops.helpers.parse_json_response")
    def test_returns_pr_data_on_success(self, mock_parse, mock_run_safe):
        mock_run_safe.return_value = MagicMock(returncode=0, stdout='{"pullRequestId": 123}', stderr="")
        mock_parse.return_value = {
            "pullRequestId": 123,
            "repository": {"webUrl": "https://dev.azure.com/myorg/proj/_git/repo"},
        }
        config = self._make_config()

        result = create_pull_request(
            config=config,
            pat="test-pat",
            source_branch="feature/test",
            title="Test PR",
        )

        assert result["pull_request_id"] == 123
        assert "pullrequest/123" in result["url"]

    @patch("agentic_devtools.cli.subprocess_utils.run_safe")
    def test_raises_runtime_error_on_failure(self, mock_run_safe):
        mock_run_safe.return_value = MagicMock(returncode=1, stdout="", stderr="Auth failed")
        config = self._make_config()

        with pytest.raises(RuntimeError, match="az repos pr create failed"):
            create_pull_request(
                config=config,
                pat="bad-pat",
                source_branch="feature/test",
                title="Test PR",
            )

    @patch("agentic_devtools.cli.subprocess_utils.run_safe")
    @patch("agentic_devtools.cli.azure_devops.helpers.parse_json_response")
    def test_includes_draft_flag(self, mock_parse, mock_run_safe):
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        mock_parse.return_value = {"pullRequestId": 1, "repository": {}}
        config = self._make_config()

        create_pull_request(config=config, pat="pat", source_branch="feat", title="PR", draft=True)

        cmd = mock_run_safe.call_args[0][0]
        assert "--draft" in cmd

    @patch("agentic_devtools.cli.subprocess_utils.run_safe")
    @patch("agentic_devtools.cli.azure_devops.helpers.parse_json_response")
    def test_no_draft_flag_when_false(self, mock_parse, mock_run_safe):
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        mock_parse.return_value = {"pullRequestId": 1, "repository": {}}
        config = self._make_config()

        create_pull_request(config=config, pat="pat", source_branch="feat", title="PR", draft=False)

        cmd = mock_run_safe.call_args[0][0]
        assert "--draft" not in cmd

    @patch("agentic_devtools.cli.subprocess_utils.run_safe")
    @patch("agentic_devtools.cli.azure_devops.helpers.parse_json_response")
    def test_includes_description(self, mock_parse, mock_run_safe):
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        mock_parse.return_value = {"pullRequestId": 1, "repository": {}}
        config = self._make_config()

        create_pull_request(
            config=config,
            pat="pat",
            source_branch="feat",
            title="PR",
            description="My description",
        )

        cmd = mock_run_safe.call_args[0][0]
        assert "--description" in cmd
        idx = cmd.index("--description")
        assert cmd[idx + 1] == "My description"

    @patch("agentic_devtools.cli.subprocess_utils.run_safe")
    @patch("agentic_devtools.cli.azure_devops.helpers.parse_json_response")
    def test_sets_pat_in_env(self, mock_parse, mock_run_safe):
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        mock_parse.return_value = {"pullRequestId": 1, "repository": {}}
        config = self._make_config()

        create_pull_request(config=config, pat="my-secret-pat", source_branch="feat", title="PR")

        env = mock_run_safe.call_args[1]["env"]
        assert env["AZURE_DEVOPS_EXT_PAT"] == "my-secret-pat"

    @patch("agentic_devtools.cli.subprocess_utils.run_safe")
    @patch("agentic_devtools.cli.azure_devops.helpers.parse_json_response")
    def test_returns_empty_url_when_pr_id_is_zero(self, mock_parse, mock_run_safe):
        """When pullRequestId is missing/zero, url should be empty."""
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        mock_parse.return_value = {
            "pullRequestId": 0,
            "repository": {"webUrl": "https://dev.azure.com/myorg/proj/_git/repo"},
        }
        config = self._make_config()

        result = create_pull_request(config=config, pat="pat", source_branch="feat", title="PR")

        assert result["url"] == ""
        assert result["pull_request_id"] == 0

    @patch("agentic_devtools.cli.subprocess_utils.run_safe")
    @patch("agentic_devtools.cli.azure_devops.helpers.parse_json_response")
    def test_returns_empty_url_when_web_url_missing(self, mock_parse, mock_run_safe):
        """When repository.webUrl is missing, url should be empty."""
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        mock_parse.return_value = {"pullRequestId": 42, "repository": {}}
        config = self._make_config()

        result = create_pull_request(config=config, pat="pat", source_branch="feat", title="PR")

        assert result["url"] == ""
        assert result["pull_request_id"] == 42

    @patch("agentic_devtools.tools.azure_devops.sys")
    @patch("agentic_devtools.cli.subprocess_utils.run_safe")
    @patch("agentic_devtools.cli.azure_devops.helpers.parse_json_response")
    def test_escapes_percent_in_user_args_on_windows(self, mock_parse, mock_run_safe, mock_sys):
        """On Windows, % in user args is doubled to prevent cmd.exe %VAR% expansion."""
        mock_sys.platform = "win32"
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        mock_parse.return_value = {"pullRequestId": 1, "repository": {}}
        config = self._make_config()

        create_pull_request(
            config=config,
            pat="pat",
            source_branch="feat/%ISSUE%",
            title="fix(%PAT%): something",
            description="desc with %SECRET%",
        )

        cmd = mock_run_safe.call_args[0][0]
        idx_src = cmd.index("--source-branch")
        assert cmd[idx_src + 1] == "feat/%%ISSUE%%"
        idx_title = cmd.index("--title")
        assert cmd[idx_title + 1] == "fix(%%PAT%%): something"
        idx_desc = cmd.index("--description")
        assert cmd[idx_desc + 1] == "desc with %%SECRET%%"
