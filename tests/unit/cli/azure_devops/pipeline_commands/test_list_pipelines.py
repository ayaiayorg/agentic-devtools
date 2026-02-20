"""Tests for list_pipelines function."""
from agentic_devtools import state
from agentic_devtools.cli import azure_devops
from unittest.mock import MagicMock, patch
import pytest

class TestListPipelinesDryRun:
    """Tests for list_pipelines command in dry-run mode."""

    def test_dry_run_basic(self, temp_state_dir, clear_state_before, capsys):
        """Test basic dry run output."""
        state.set_dry_run(True)

        azure_devops.list_pipelines()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "Would list pipelines" in captured.out

    def test_dry_run_with_filter(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output with name filter."""
        state.set_dry_run(True)
        state.set_value("pipeline.name_filter", "mgmt*")

        azure_devops.list_pipelines()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "mgmt*" in captured.out

    def test_dry_run_shows_org_project(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows organization and project."""
        state.set_dry_run(True)

        azure_devops.list_pipelines()

        captured = capsys.readouterr()
        assert "Org" in captured.out
        assert "Project" in captured.out

class TestListPipelinesApiCall:
    """Tests for list_pipelines command with mocked API calls."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_successful_list(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test successful pipeline listing."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_list = MagicMock()
        mock_list.returncode = 0
        mock_list.stdout = '[{"id": 123, "name": "test-pipeline", "path": "/test"}]'

        mock_run.side_effect = [mock_version, mock_ext, mock_list]

        azure_devops.list_pipelines()

        captured = capsys.readouterr()
        assert "Found 1 pipeline" in captured.out
        assert "test-pipeline" in captured.out
        assert "123" in captured.out

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_list_with_filter(self, mock_run, temp_state_dir, clear_state_before):
        """Test list passes name filter to az CLI."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_list = MagicMock()
        mock_list.returncode = 0
        mock_list.stdout = "[]"

        mock_run.side_effect = [mock_version, mock_ext, mock_list]

        state.set_value("pipeline.name_filter", "mgmt*")

        azure_devops.list_pipelines()

        list_call = mock_run.call_args_list[2]
        cmd = list_call[0][0]
        assert "--name" in cmd
        assert "mgmt*" in cmd

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_empty_result(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test empty result handling."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_list = MagicMock()
        mock_list.returncode = 0
        mock_list.stdout = "[]"

        mock_run.side_effect = [mock_version, mock_ext, mock_list]

        azure_devops.list_pipelines()

        captured = capsys.readouterr()
        assert "No pipelines found" in captured.out

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_list_failure(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test list fails when az command fails."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_list = MagicMock()
        mock_list.returncode = 1
        mock_list.stderr = "Failed to list pipelines"

        mock_run.side_effect = [mock_version, mock_ext, mock_list]

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.list_pipelines()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error listing pipelines" in captured.err

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_json_parse_error(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test handling of invalid JSON response."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_list = MagicMock()
        mock_list.returncode = 0
        mock_list.stdout = "invalid json"

        mock_run.side_effect = [mock_version, mock_ext, mock_list]

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.list_pipelines()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error parsing response" in captured.err
