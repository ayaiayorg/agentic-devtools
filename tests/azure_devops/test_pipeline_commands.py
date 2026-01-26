"""
Tests for Azure DevOps pipeline commands (list_pipelines, get_pipeline_id, create_pipeline, update_pipeline).
"""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import azure_devops


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


class TestUpdatePipelineDryRun:
    """Tests for update_pipeline command in dry-run mode."""

    def test_dry_run_with_new_name(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run output with new name."""
        state.set_dry_run(True)
        state.set_value("pipeline.id", "123")
        state.set_value("pipeline.new_name", "renamed-pipeline")

        azure_devops.update_pipeline()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "123" in captured.out
        assert "renamed-pipeline" in captured.out

    def test_dry_run_with_all_options(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with all optional parameters."""
        state.set_dry_run(True)
        state.set_value("pipeline.id", "123")
        state.set_value("pipeline.new_name", "renamed-pipeline")
        state.set_value("pipeline.yaml_path", "/new/path/pipeline.yml")
        state.set_value("pipeline.new_folder_path", "/NewFolder")
        state.set_value("pipeline.description", "Updated description")

        azure_devops.update_pipeline()

        captured = capsys.readouterr()
        assert "renamed-pipeline" in captured.out
        assert "/new/path/pipeline.yml" in captured.out or "New YAML Path" in captured.out
        assert "/NewFolder" in captured.out or "New Folder" in captured.out

    def test_missing_pipeline_id(self, temp_state_dir, clear_state_before, capsys):
        """Test exits when pipeline.id is missing."""
        state.set_dry_run(True)
        state.set_value("pipeline.new_name", "renamed-pipeline")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.update_pipeline()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "pipeline.id" in captured.err

    def test_missing_update_parameter(self, temp_state_dir, clear_state_before, capsys):
        """Test exits when no update parameter is provided."""
        state.set_dry_run(True)
        state.set_value("pipeline.id", "123")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.update_pipeline()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "At least one update parameter" in captured.err


class TestUpdatePipelineApiCall:
    """Tests for update_pipeline command with mocked API calls."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_successful_rename(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test successful pipeline rename."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_update = MagicMock()
        mock_update.returncode = 0
        mock_update.stdout = (
            '{"id": 123, "name": "renamed-pipeline", "_links": {"web": {"href": "https://test/pipeline"}}}'
        )

        mock_run.side_effect = [mock_version, mock_ext, mock_update]

        state.set_value("pipeline.id", "123")
        state.set_value("pipeline.new_name", "renamed-pipeline")

        azure_devops.update_pipeline()

        captured = capsys.readouterr()
        assert "updated successfully" in captured.out.lower()

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_update_yaml_path(self, mock_run, temp_state_dir, clear_state_before):
        """Test update passes yaml path to az CLI."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_update = MagicMock()
        mock_update.returncode = 0
        mock_update.stdout = '{"id": 123}'

        mock_run.side_effect = [mock_version, mock_ext, mock_update]

        state.set_value("pipeline.id", "123")
        state.set_value("pipeline.yaml_path", "/new/pipeline.yml")

        azure_devops.update_pipeline()

        update_call = mock_run.call_args_list[2]
        cmd = update_call[0][0]
        assert "--yml-path" in cmd
        assert "/new/pipeline.yml" in cmd

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_update_folder(self, mock_run, temp_state_dir, clear_state_before):
        """Test update passes new folder path to az CLI."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_update = MagicMock()
        mock_update.returncode = 0
        mock_update.stdout = '{"id": 123}'

        mock_run.side_effect = [mock_version, mock_ext, mock_update]

        state.set_value("pipeline.id", "123")
        state.set_value("pipeline.new_folder_path", "/NewFolder")

        azure_devops.update_pipeline()

        update_call = mock_run.call_args_list[2]
        cmd = update_call[0][0]
        assert "--new-folder-path" in cmd
        assert "/NewFolder" in cmd

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_update_failure(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test update fails when az command fails."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_update = MagicMock()
        mock_update.returncode = 1
        mock_update.stderr = "Pipeline not found"

        mock_run.side_effect = [mock_version, mock_ext, mock_update]

        state.set_value("pipeline.id", "123")
        state.set_value("pipeline.new_name", "renamed-pipeline")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.update_pipeline()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error updating pipeline" in captured.err

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_update_json_parse_error(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test handling of invalid JSON response."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_update = MagicMock()
        mock_update.returncode = 0
        mock_update.stdout = "invalid json"

        mock_run.side_effect = [mock_version, mock_ext, mock_update]

        state.set_value("pipeline.id", "123")
        state.set_value("pipeline.new_name", "renamed-pipeline")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.update_pipeline()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error parsing response" in captured.err


class TestParseBoolParam:
    """Tests for _parse_bool_param helper function."""

    def test_true_values(self, temp_state_dir, clear_state_before):
        """Test various true values."""
        from agentic_devtools.cli.azure_devops.pipeline_commands import _parse_bool_param

        assert _parse_bool_param("1") is True
        assert _parse_bool_param("true") is True
        assert _parse_bool_param("TRUE") is True
        assert _parse_bool_param("True") is True
        assert _parse_bool_param("yes") is True
        assert _parse_bool_param("YES") is True

    def test_false_values(self, temp_state_dir, clear_state_before):
        """Test various false values."""
        from agentic_devtools.cli.azure_devops.pipeline_commands import _parse_bool_param

        assert _parse_bool_param("0") is False
        assert _parse_bool_param("false") is False
        assert _parse_bool_param("FALSE") is False
        assert _parse_bool_param("no") is False
        assert _parse_bool_param("anything") is False

    def test_none_returns_default(self, temp_state_dir, clear_state_before):
        """Test None returns default value."""
        from agentic_devtools.cli.azure_devops.pipeline_commands import _parse_bool_param

        assert _parse_bool_param(None) is False
        assert _parse_bool_param(None, default=True) is True
        assert _parse_bool_param(None, default=False) is False


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


class TestUpdatePipelineUrlOutput:
    """Tests for URL output in update_pipeline."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_url_output(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test URL output when _links.web.href is present."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_update = MagicMock()
        mock_update.returncode = 0
        mock_update.stdout = (
            '{"id": 123, "name": "renamed-pipeline", "_links": {"web": {"href": "https://test/updated/url"}}}'
        )

        mock_run.side_effect = [mock_version, mock_ext, mock_update]

        state.set_value("pipeline.id", "123")
        state.set_value("pipeline.new_name", "renamed-pipeline")

        azure_devops.update_pipeline()

        captured = capsys.readouterr()
        assert "https://test/updated/url" in captured.out
