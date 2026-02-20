"""Tests for run e2e tests fabric function."""
from agentic_devtools import state
from agentic_devtools.cli import azure_devops
from unittest.mock import MagicMock, patch
import pytest

class TestRunE2eTestsFabricJsonParseError:
    """Tests for JSON parse error handling in run_e2e_tests_fabric."""

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
            azure_devops.run_e2e_tests_fabric()

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
        mock_queue.stdout = '{"id": 88888, "url": "https://fallback/url"}'

        mock_run.side_effect = [mock_version, mock_ext, mock_queue]

        state.set_value("branch", "feature/test")

        azure_devops.run_e2e_tests_fabric()

        captured = capsys.readouterr()
        assert "https://fallback/url" in captured.out

class TestRunE2eTestsFabric:
    """Tests for run_e2e_tests_fabric command."""

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output shows correct information."""
        state.set_value("branch", "feature/test-branch")
        state.set_dry_run(True)

        azure_devops.run_e2e_tests_fabric()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "mgmt-e2e-tests-fabric" in captured.out
        assert "feature/test-branch" in captured.out
        # Fabric tests always run in DEV (no stage parameter)

    def test_dry_run_shows_org_project(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows organization and project."""
        state.set_value("branch", "feature/test-branch")
        state.set_dry_run(True)

        azure_devops.run_e2e_tests_fabric()

        captured = capsys.readouterr()
        assert "Org" in captured.out
        assert "Project" in captured.out

    def test_missing_branch(self, temp_state_dir, clear_state_before):
        """Test exits when branch is missing."""
        state.set_dry_run(True)
        with pytest.raises(SystemExit):
            azure_devops.run_e2e_tests_fabric()

class TestRunE2eTestsFabricActualCall:
    """Tests for run_e2e_tests_fabric with mocked API calls."""

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
        mock_queue.stdout = '{"id": 88888, "_links": {"web": {"href": "https://test/logs"}}}'

        mock_run.side_effect = [mock_version, mock_ext, mock_queue]

        state.set_value("branch", "feature/test")

        azure_devops.run_e2e_tests_fabric()

        captured = capsys.readouterr()
        assert "queued successfully" in captured.out.lower()
        assert "88888" in captured.out

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_queue_uses_fabric_pipeline(self, mock_run, temp_state_dir, clear_state_before):
        """Test that run_e2e_tests_fabric uses the correct pipeline name."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_queue = MagicMock()
        mock_queue.returncode = 0
        mock_queue.stdout = '{"id": 88888}'

        mock_run.side_effect = [mock_version, mock_ext, mock_queue]

        state.set_value("branch", "feature/test")

        azure_devops.run_e2e_tests_fabric()

        # Check that the pipeline name is mgmt-e2e-tests-fabric
        queue_call = mock_run.call_args_list[2]
        cmd = queue_call[0][0]
        assert "mgmt-e2e-tests-fabric" in cmd

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
            azure_devops.run_e2e_tests_fabric()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error queuing pipeline" in captured.err
