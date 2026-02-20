"""Tests for mark_pull_request_draft function."""
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import azure_devops


class TestMarkPullRequestDraft:
    """Tests for mark_pull_request_draft command."""

    def test_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output."""
        state.set_pull_request_id(12345)
        state.set_dry_run(True)

        azure_devops.mark_pull_request_draft()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "12345" in captured.out
        assert "draft" in captured.out.lower()

    def test_dry_run_shows_org_project(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows organization and project."""
        state.set_pull_request_id(12345)
        state.set_dry_run(True)

        azure_devops.mark_pull_request_draft()

        captured = capsys.readouterr()
        assert "Org/Project:" in captured.out

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before):
        """Test raises error when pull request ID is missing."""
        state.set_dry_run(True)
        with pytest.raises(KeyError, match="pull_request_id"):
            azure_devops.mark_pull_request_draft()

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
