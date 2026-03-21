"""Tests for agentic_devtools.tools.azure_devops.update_review_narrative."""

from unittest.mock import MagicMock, patch

from agentic_devtools.tools.azure_devops import update_review_narrative


class TestUpdateReviewNarrative:
    """Tests for the update_review_narrative tool function."""

    def _make_config(self):
        config = MagicMock()
        config.organization = "https://dev.azure.com/myorg"
        config.project = "MyProject"
        config.repository = "my-repo"
        return config

    @patch("agentic_devtools.cli.azure_devops.review_state.save_review_state")
    @patch("agentic_devtools.cli.azure_devops.helpers.patch_comment")
    @patch("agentic_devtools.cli.azure_devops.review_templates.render_overall_summary", return_value="rendered content")
    @patch(
        "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url", return_value="https://example.com/pr/1"
    )
    @patch("agentic_devtools.cli.azure_devops.helpers.get_repository_id", return_value="repo-id")
    @patch("agentic_devtools.cli.azure_devops.auth.get_auth_headers", return_value={"Authorization": "Basic xxx"})
    @patch("agentic_devtools.tools.azure_devops._get_requests")
    def test_updates_narrative_with_provided_state(
        self, mock_req, mock_auth, mock_repo_id, mock_base_url, mock_render, mock_patch, mock_save
    ):
        mock_review_state = MagicMock()
        mock_review_state.repoId = "repo-id"
        mock_review_state.overallSummary.threadId = 1
        mock_review_state.overallSummary.commentId = 2
        config = self._make_config()

        result = update_review_narrative(
            config=config,
            pat="test-pat",
            pull_request_id=1,
            content="New narrative",
            review_state=mock_review_state,
        )

        assert result["success"] is True
        assert mock_review_state.overallSummary.narrativeSummary == "New narrative"
        mock_patch.assert_called_once()
        mock_save.assert_called_once()

    @patch("agentic_devtools.cli.azure_devops.review_state.save_review_state")
    @patch("agentic_devtools.cli.azure_devops.helpers.patch_comment")
    @patch("agentic_devtools.cli.azure_devops.review_templates.render_overall_summary", return_value="rendered")
    @patch(
        "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url", return_value="https://example.com/pr/1"
    )
    @patch("agentic_devtools.cli.azure_devops.review_state.load_review_state")
    @patch("agentic_devtools.cli.azure_devops.helpers.get_repository_id", return_value="repo-id")
    @patch("agentic_devtools.cli.azure_devops.auth.get_auth_headers", return_value={"Authorization": "Basic xxx"})
    @patch("agentic_devtools.tools.azure_devops._get_requests")
    def test_loads_state_when_not_provided(
        self, mock_req, mock_auth, mock_repo_id, mock_load, mock_base_url, mock_render, mock_patch, mock_save
    ):
        mock_review_state = MagicMock()
        mock_review_state.repoId = None
        mock_review_state.overallSummary.threadId = 5
        mock_review_state.overallSummary.commentId = 6
        mock_load.return_value = mock_review_state
        config = self._make_config()

        result = update_review_narrative(
            config=config,
            pat="test-pat",
            pull_request_id=99,
            content="Updated",
        )

        assert result["success"] is True
        mock_load.assert_called_once_with(99)
        mock_repo_id.assert_called_once()
        # Verify repoId is persisted back onto the review_state
        assert mock_review_state.repoId == "repo-id"

    @patch("agentic_devtools.cli.azure_devops.review_state.save_review_state")
    @patch("agentic_devtools.cli.azure_devops.helpers.patch_comment")
    @patch("agentic_devtools.cli.azure_devops.review_templates.render_overall_summary", return_value="rendered")
    @patch(
        "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url", return_value="https://example.com/pr/1"
    )
    @patch("agentic_devtools.cli.azure_devops.auth.get_auth_headers", return_value={"Authorization": "Basic xxx"})
    @patch("agentic_devtools.tools.azure_devops._get_requests")
    def test_skips_repo_id_lookup_when_in_state(
        self, mock_req, mock_auth, mock_base_url, mock_render, mock_patch, mock_save
    ):
        mock_review_state = MagicMock()
        mock_review_state.repoId = "existing-repo-id"
        mock_review_state.overallSummary.threadId = 1
        mock_review_state.overallSummary.commentId = 1
        config = self._make_config()

        update_review_narrative(
            config=config,
            pat="test-pat",
            pull_request_id=1,
            content="Content",
            review_state=mock_review_state,
        )

        mock_patch.assert_called_once()
        # Verify repo_id came from review_state, not from get_repository_id
        call_args = mock_patch.call_args
        assert call_args[0][3] == "existing-repo-id"

    @patch("agentic_devtools.tools.azure_devops.sys")
    @patch("agentic_devtools.cli.azure_devops.review_state.save_review_state")
    @patch("agentic_devtools.cli.azure_devops.helpers.patch_comment")
    @patch("agentic_devtools.cli.azure_devops.review_templates.render_overall_summary", return_value="rendered")
    @patch(
        "agentic_devtools.cli.azure_devops.review_scaffold.build_pr_base_url", return_value="https://example.com/pr/1"
    )
    @patch("agentic_devtools.cli.azure_devops.helpers.get_repository_id", return_value="repo-id")
    @patch("agentic_devtools.cli.azure_devops.auth.get_auth_headers", return_value={"Authorization": "Basic xxx"})
    @patch("agentic_devtools.tools.azure_devops._get_requests")
    def test_escapes_config_args_for_get_repository_id_on_windows(
        self, mock_req, mock_auth, mock_repo_id, mock_base_url, mock_render, mock_patch, mock_save, mock_sys
    ):
        """Config-derived values are escaped before passing to get_repository_id on Windows."""
        mock_sys.platform = "win32"
        mock_review_state = MagicMock()
        mock_review_state.repoId = None  # Forces get_repository_id call
        mock_review_state.overallSummary.threadId = 1
        mock_review_state.overallSummary.commentId = 2
        config = self._make_config()
        config.organization = "https://dev.azure.com/%ORG%"
        config.project = "%PROJECT%"
        config.repository = "%REPO%"

        update_review_narrative(
            config=config, pat="pat", pull_request_id=1, content="Narrative",
            review_state=mock_review_state,
        )

        mock_repo_id.assert_called_once_with(
            "https://dev.azure.com/%%ORG%%", "%%PROJECT%%", "%%REPO%%"
        )
