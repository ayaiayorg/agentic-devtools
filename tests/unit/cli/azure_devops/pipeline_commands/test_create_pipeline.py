"""Tests for create_pipeline function."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import azure_devops


class TestCreatePipelineDryRun:
    """Tests for create_pipeline command in dry-run mode."""

    def test_dry_run_basic(self, temp_state_dir, clear_state_before, capsys):
        """Test basic dry run output."""
        state.set_dry_run(True)
        state.set_value("pipeline.name", "new-pipeline")
        state.set_value("pipeline.yaml_path", "/path/to/pipeline.yml")

        azure_devops.create_pipeline()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "new-pipeline" in captured.out
        assert "/path/to/pipeline.yml" in captured.out

    def test_dry_run_with_all_options(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with all optional parameters."""
        state.set_dry_run(True)
        state.set_value("pipeline.name", "new-pipeline")
        state.set_value("pipeline.yaml_path", "/path/to/pipeline.yml")
        state.set_value("pipeline.description", "Test description")
        state.set_value("pipeline.folder_path", "/MyFolder")
        state.set_value("pipeline.skip_first_run", "false")
        state.set_value("branch", "develop")

        azure_devops.create_pipeline()

        captured = capsys.readouterr()
        assert "Test description" in captured.out or "(none)" not in captured.out
        assert "/MyFolder" in captured.out or "(root)" not in captured.out
        assert "develop" in captured.out

    def test_missing_pipeline_name(self, temp_state_dir, clear_state_before, capsys):
        """Test exits when pipeline.name is missing."""
        state.set_dry_run(True)
        state.set_value("pipeline.yaml_path", "/path/to/pipeline.yml")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.create_pipeline()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "pipeline.name" in captured.err

    def test_missing_yaml_path(self, temp_state_dir, clear_state_before, capsys):
        """Test exits when pipeline.yaml_path is missing."""
        state.set_dry_run(True)
        state.set_value("pipeline.name", "new-pipeline")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.create_pipeline()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "pipeline.yaml_path" in captured.err


class TestCreatePipelineApiCall:
    """Tests for create_pipeline command with mocked API calls."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_successful_create(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test successful pipeline creation."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_create = MagicMock()
        mock_create.returncode = 0
        mock_create.stdout = '{"id": 789, "name": "new-pipeline", "_links": {"web": {"href": "https://test/pipeline"}}}'

        mock_run.side_effect = [mock_version, mock_ext, mock_create]

        state.set_value("pipeline.name", "new-pipeline")
        state.set_value("pipeline.yaml_path", "/path/to/pipeline.yml")

        azure_devops.create_pipeline()

        captured = capsys.readouterr()
        assert "created successfully" in captured.out.lower()
        assert "789" in captured.out
        assert state.get_value("pipeline.id") == "789"

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_create_with_description_and_folder(self, mock_run, temp_state_dir, clear_state_before):
        """Test create passes description and folder to az CLI."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_create = MagicMock()
        mock_create.returncode = 0
        mock_create.stdout = '{"id": 789}'

        mock_run.side_effect = [mock_version, mock_ext, mock_create]

        state.set_value("pipeline.name", "new-pipeline")
        state.set_value("pipeline.yaml_path", "/path/to/pipeline.yml")
        state.set_value("pipeline.description", "My description")
        state.set_value("pipeline.folder_path", "/MyFolder")

        azure_devops.create_pipeline()

        create_call = mock_run.call_args_list[2]
        cmd = create_call[0][0]
        assert "--description" in cmd
        assert "My description" in cmd
        assert "--folder-path" in cmd
        assert "/MyFolder" in cmd

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_create_failure(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test create fails when az command fails."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_create = MagicMock()
        mock_create.returncode = 1
        mock_create.stderr = "Pipeline already exists"

        mock_run.side_effect = [mock_version, mock_ext, mock_create]

        state.set_value("pipeline.name", "new-pipeline")
        state.set_value("pipeline.yaml_path", "/path/to/pipeline.yml")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.create_pipeline()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error creating pipeline" in captured.err


class TestCreatePipelineJsonParseError:
    """Tests for JSON parse error handling in create_pipeline."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_json_parse_error(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test handling of invalid JSON response."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_create = MagicMock()
        mock_create.returncode = 0
        mock_create.stdout = "not valid json"

        mock_run.side_effect = [mock_version, mock_ext, mock_create]

        state.set_value("pipeline.name", "new-pipeline")
        state.set_value("pipeline.yaml_path", "/path/to/pipeline.yml")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.create_pipeline()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error parsing response" in captured.err

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_url_output(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test URL output when _links.web.href is present."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_create = MagicMock()
        mock_create.returncode = 0
        mock_create.stdout = (
            '{"id": 789, "name": "new-pipeline", "_links": {"web": {"href": "https://test/pipeline/url"}}}'
        )
        mock_run.side_effect = [mock_version, mock_ext, mock_create]

        state.set_value("pipeline.name", "new-pipeline")
        state.set_value("pipeline.yaml_path", "/path/to/pipeline.yml")

        azure_devops.create_pipeline()

        captured = capsys.readouterr()
        assert "https://test/pipeline/url" in captured.out
