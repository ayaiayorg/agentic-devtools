"""Tests for get_pipeline_id function."""
from agentic_devtools import state
from agentic_devtools.cli import azure_devops
from unittest.mock import MagicMock, patch
import pytest

class TestGetPipelineIdDryRun:
    """Tests for get_pipeline_id command in dry-run mode."""

    def test_dry_run_basic(self, temp_state_dir, clear_state_before, capsys):
        """Test basic dry run output."""
        state.set_dry_run(True)
        state.set_value("pipeline.name", "test-pipeline")

        azure_devops.get_pipeline_id()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "test-pipeline" in captured.out

    def test_dry_run_shows_org_project(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows organization and project."""
        state.set_dry_run(True)
        state.set_value("pipeline.name", "test-pipeline")

        azure_devops.get_pipeline_id()

        captured = capsys.readouterr()
        assert "Org" in captured.out
        assert "Project" in captured.out

    def test_missing_pipeline_name(self, temp_state_dir, clear_state_before, capsys):
        """Test exits when pipeline.name is missing."""
        state.set_dry_run(True)

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.get_pipeline_id()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "pipeline.name" in captured.err

class TestGetPipelineIdApiCall:
    """Tests for get_pipeline_id command with mocked API calls."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_successful_lookup(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test successful pipeline ID lookup."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_list = MagicMock()
        mock_list.returncode = 0
        mock_list.stdout = '[{"id": 456, "name": "my-pipeline"}]'

        mock_run.side_effect = [mock_version, mock_ext, mock_list]

        state.set_value("pipeline.name", "my-pipeline")

        azure_devops.get_pipeline_id()

        captured = capsys.readouterr()
        assert "456" in captured.out
        assert "Stored pipeline.id" in captured.out

        # Check state was set
        assert state.get_value("pipeline.id") == "456"

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_pipeline_not_found(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test error when pipeline is not found."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_list = MagicMock()
        mock_list.returncode = 0
        mock_list.stdout = "[]"

        mock_run.side_effect = [mock_version, mock_ext, mock_list]

        state.set_value("pipeline.name", "nonexistent-pipeline")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.get_pipeline_id()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_exact_match_required(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test that only exact name matches are returned."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_list = MagicMock()
        mock_list.returncode = 0
        mock_list.stdout = '[{"id": 111, "name": "my-pipeline-extra"}, {"id": 222, "name": "my-pipeline"}]'

        mock_run.side_effect = [mock_version, mock_ext, mock_list]

        state.set_value("pipeline.name", "my-pipeline")

        azure_devops.get_pipeline_id()

        captured = capsys.readouterr()
        assert "222" in captured.out  # Should find exact match

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_suggests_similar_names(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test shows similar names when exact match not found."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_list = MagicMock()
        mock_list.returncode = 0
        mock_list.stdout = '[{"id": 111, "name": "my-pipeline-1"}, {"id": 222, "name": "my-pipeline-2"}]'

        mock_run.side_effect = [mock_version, mock_ext, mock_list]

        state.set_value("pipeline.name", "my-pipeline")

        with pytest.raises(SystemExit):
            azure_devops.get_pipeline_id()

        captured = capsys.readouterr()
        assert "similar names" in captured.err
        assert "my-pipeline-1" in captured.err

class TestGetPipelineIdJsonParseError:
    """Tests for JSON parse error handling in get_pipeline_id."""

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
        mock_list.stdout = "not valid json"

        mock_run.side_effect = [mock_version, mock_ext, mock_list]

        state.set_value("pipeline.name", "test-pipeline")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.get_pipeline_id()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error parsing response" in captured.err
