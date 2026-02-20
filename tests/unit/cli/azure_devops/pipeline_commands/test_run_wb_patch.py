"""Tests for run wb patch function."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import azure_devops


class TestRunWbPatchJsonParseError:
    """Tests for JSON parse error handling in run_wb_patch."""

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
        state.set_value("wb_patch.workbench", "STND")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.run_wb_patch()

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
        mock_queue.stdout = '{"id": 77777, "url": "https://fallback/url"}'

        mock_run.side_effect = [mock_version, mock_ext, mock_queue]

        state.set_value("branch", "feature/test")
        state.set_value("wb_patch.workbench", "STND")

        azure_devops.run_wb_patch()

        captured = capsys.readouterr()
        assert "https://fallback/url" in captured.out


class TestRunWbPatch:
    """Tests for run_wb_patch command."""

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output shows correct information."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("wb_patch.workbench", "STND")
        state.set_dry_run(True)

        azure_devops.run_wb_patch()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "wb-patch" in captured.out
        assert "feature/test-branch" in captured.out
        assert "STND" in captured.out

    def test_dry_run_default_values(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows default values."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("wb_patch.workbench", "TESR")
        state.set_dry_run(True)

        azure_devops.run_wb_patch()

        captured = capsys.readouterr()
        assert "latest" in captured.out  # default helper_lib_version
        assert "true" in captured.out.lower()  # plan_only default is true

    def test_dry_run_with_all_params(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with all parameters set."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("wb_patch.workbench", "STND")
        state.set_value("wb_patch.helper_lib_version", "1.2.3")
        state.set_value("wb_patch.plan_only", "false")
        state.set_value("wb_patch.deploy_helper_lib", "true")
        state.set_value("wb_patch.deploy_synapse_dap", "true")
        state.set_value("wb_patch.deploy_fabric_dap", "true")
        state.set_dry_run(True)

        azure_devops.run_wb_patch()

        captured = capsys.readouterr()
        assert "1.2.3" in captured.out
        # plan_only=false should show as false
        assert "Plan Only" in captured.out

    def test_dry_run_shows_org_project(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows organization and project."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("wb_patch.workbench", "STND")
        state.set_dry_run(True)

        azure_devops.run_wb_patch()

        captured = capsys.readouterr()
        assert "Org" in captured.out
        assert "Project" in captured.out

    def test_missing_branch(self, temp_state_dir, clear_state_before):
        """Test exits when branch is missing."""
        state.set_value("wb_patch.workbench", "STND")
        state.set_dry_run(True)
        with pytest.raises(SystemExit):
            azure_devops.run_wb_patch()

    def test_missing_workbench(self, temp_state_dir, clear_state_before):
        """Test exits when workbench is missing."""
        state.set_value("branch", "feature/test-branch")
        state.set_dry_run(True)
        with pytest.raises(SystemExit):
            azure_devops.run_wb_patch()

    def test_bool_parsing_string_true(self, temp_state_dir, clear_state_before, capsys):
        """Test boolean parsing with 'true' string."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("wb_patch.workbench", "STND")
        state.set_value("wb_patch.deploy_helper_lib", "true")
        state.set_dry_run(True)

        azure_devops.run_wb_patch()

        captured = capsys.readouterr()
        assert "Deploy Helper Lib" in captured.out

    def test_bool_parsing_string_yes(self, temp_state_dir, clear_state_before, capsys):
        """Test boolean parsing with 'yes' string."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("wb_patch.workbench", "STND")
        state.set_value("wb_patch.deploy_synapse_dap", "yes")
        state.set_dry_run(True)

        azure_devops.run_wb_patch()

        captured = capsys.readouterr()
        assert "Deploy Synapse DAP" in captured.out

    def test_bool_parsing_string_1(self, temp_state_dir, clear_state_before, capsys):
        """Test boolean parsing with '1' string."""
        state.set_value("branch", "feature/test-branch")
        state.set_value("wb_patch.workbench", "STND")
        state.set_value("wb_patch.deploy_fabric_dap", "1")
        state.set_dry_run(True)

        azure_devops.run_wb_patch()

        captured = capsys.readouterr()
        assert "Deploy Fabric DAP" in captured.out


class TestRunWbPatchActualCall:
    """Tests for run_wb_patch with mocked API calls."""

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
        state.set_value("wb_patch.workbench", "STND")

        azure_devops.run_wb_patch()

        captured = capsys.readouterr()
        assert "queued successfully" in captured.out.lower()
        assert "88888" in captured.out

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_queue_includes_workbench_param(self, mock_run, temp_state_dir, clear_state_before):
        """Test that run_wb_patch passes workbench parameter."""
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
        state.set_value("wb_patch.workbench", "TESR")

        azure_devops.run_wb_patch()

        # Check that workbench=TESR was in the command
        queue_call = mock_run.call_args_list[2]
        cmd = queue_call[0][0]
        assert "workbench=TESR" in cmd

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_queue_includes_all_params(self, mock_run, temp_state_dir, clear_state_before):
        """Test that run_wb_patch passes all parameters."""
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
        state.set_value("wb_patch.workbench", "STND")
        state.set_value("wb_patch.helper_lib_version", "2.0.0")
        state.set_value("wb_patch.plan_only", "false")
        state.set_value("wb_patch.deploy_helper_lib", "true")

        azure_devops.run_wb_patch()

        queue_call = mock_run.call_args_list[2]
        cmd = queue_call[0][0]
        assert "workbench=STND" in cmd
        assert "helper_lib_version=2.0.0" in cmd
        assert "plan_only=false" in cmd
        assert "deploy_helper_lib=true" in cmd

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
        state.set_value("wb_patch.workbench", "STND")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.run_wb_patch()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error queuing pipeline" in captured.err
