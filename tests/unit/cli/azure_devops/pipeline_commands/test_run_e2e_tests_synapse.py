"""Tests for run e2e tests synapse function."""
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import azure_devops


class TestRunE2eTestsSynapseJsonParseError:
    """Tests for JSON parse error handling in run_e2e_tests_synapse."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_json_parse_error(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test handling of invalid JSON response."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_queue = MagicMock()
        mock_queue.returncode = 0
        mock_queue.stdout = "not valid json"

        mock_run.side_effect = [mock_version, mock_ext, mock_queue]

        state.set_value("branch", "feature/test")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.run_e2e_tests_synapse()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error parsing response" in captured.err

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_url_fallback_output(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test URL fallback when _links.web.href is not present."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_queue = MagicMock()
        mock_queue.returncode = 0
        mock_queue.stdout = '{"id": 12345, "url": "https://fallback/url"}'

        mock_run.side_effect = [mock_version, mock_ext, mock_queue]

        state.set_value("branch", "feature/test")

        azure_devops.run_e2e_tests_synapse()

        captured = capsys.readouterr()
        assert "https://fallback/url" in captured.out

class TestRunE2eTestsSynapse:
    """Tests for run_e2e_tests_synapse command."""

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output shows correct information."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("e2e.stage", "DEV")
        state.set_dry_run(True)

        azure_devops.run_e2e_tests_synapse()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "mgmt-e2e-tests-synapse" in captured.out
        assert "feature/test-branch" in captured.out
        assert "DEV" in captured.out

    def test_dry_run_default_stage(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run uses DEV as default stage."""
        state.set_value("branch", "feature/test-branch")
        state.set_dry_run(True)

        azure_devops.run_e2e_tests_synapse()

        captured = capsys.readouterr()
        assert "DEV" in captured.out

    def test_dry_run_int_stage(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with INT stage."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("e2e.stage", "INT")
        state.set_dry_run(True)

        azure_devops.run_e2e_tests_synapse()

        captured = capsys.readouterr()
        assert "INT" in captured.out

    def test_dry_run_shows_org_project(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows organization and project."""
        state.set_value("branch", "feature/test-branch")
        state.set_dry_run(True)

        azure_devops.run_e2e_tests_synapse()

        captured = capsys.readouterr()
        assert "Org" in captured.out
        assert "Project" in captured.out

    def test_missing_branch(self, temp_state_dir, clear_state_before):
        """Test exits when branch is missing."""
        state.set_dry_run(True)
        with pytest.raises(SystemExit):
            azure_devops.run_e2e_tests_synapse()

    def test_invalid_stage(self, temp_state_dir, clear_state_before):
        """Test exits when stage is invalid."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("e2e.stage", "PROD")
        state.set_dry_run(True)
        with pytest.raises(SystemExit):
            azure_devops.run_e2e_tests_synapse()

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
