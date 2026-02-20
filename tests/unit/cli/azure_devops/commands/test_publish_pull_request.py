"""Tests for publish_pull_request function."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import azure_devops


class TestPublishPullRequest:
    """Tests for publish_pull_request command."""

    def test_dry_run(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output."""
        state.set_pull_request_id(12345)
        state.set_dry_run(True)

        azure_devops.publish_pull_request()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "12345" in captured.out

    def test_dry_run_shows_auto_complete_will_be_enabled(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows auto-complete will be enabled by default."""
        state.set_pull_request_id(12345)
        state.set_dry_run(True)

        azure_devops.publish_pull_request()

        captured = capsys.readouterr()
        assert "Auto-complete: Will be enabled" in captured.out

    def test_dry_run_shows_auto_complete_skipped(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows auto-complete skipped when skip_auto_complete is true."""
        state.set_pull_request_id(12345)
        state.set_value("skip_auto_complete", True)
        state.set_dry_run(True)

        azure_devops.publish_pull_request()

        captured = capsys.readouterr()
        assert "Auto-complete: Skipped" in captured.out

    def test_dry_run_skip_auto_complete_string_true(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with skip_auto_complete='true' string."""
        state.set_pull_request_id(12345)
        state.set_value("skip_auto_complete", "true")
        state.set_dry_run(True)

        azure_devops.publish_pull_request()

        captured = capsys.readouterr()
        assert "Auto-complete: Skipped" in captured.out

    def test_dry_run_skip_auto_complete_string_yes(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with skip_auto_complete='yes' string."""
        state.set_pull_request_id(12345)
        state.set_value("skip_auto_complete", "yes")
        state.set_dry_run(True)

        azure_devops.publish_pull_request()

        captured = capsys.readouterr()
        assert "Auto-complete: Skipped" in captured.out

    def test_dry_run_skip_auto_complete_string_1(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with skip_auto_complete='1' string."""
        state.set_pull_request_id(12345)
        state.set_value("skip_auto_complete", "1")
        state.set_dry_run(True)

        azure_devops.publish_pull_request()

        captured = capsys.readouterr()
        assert "Auto-complete: Skipped" in captured.out

    def test_dry_run_shows_org_project(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows organization and project."""
        state.set_pull_request_id(12345)
        state.set_dry_run(True)

        azure_devops.publish_pull_request()

        captured = capsys.readouterr()
        assert "Org/Project:" in captured.out

    def test_missing_pull_request_id(self, temp_state_dir, clear_state_before):
        """Test raises error when pull request ID is missing."""
        state.set_dry_run(True)
        with pytest.raises(KeyError, match="pull_request_id"):
            azure_devops.publish_pull_request()


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
