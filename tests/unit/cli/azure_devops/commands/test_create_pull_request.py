"""Tests for create_pull_request function."""
from agentic_devtools import state
from agentic_devtools.cli import azure_devops
from unittest.mock import MagicMock, patch
import pytest

class TestCreatePullRequest:
    """Tests for create_pull_request command."""

    def test_dry_run_basic(self, temp_state_dir, clear_state_before, capsys):
        """Test basic dry run output."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "feature/test" in captured.out
        assert "Test PR" in captured.out

    def test_dry_run_with_target_branch(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows target branch."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("target_branch", "develop")
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "develop" in captured.out

    def test_dry_run_draft_mode_default(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows draft mode is True by default."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "Draft Mode: True" in captured.out

    def test_dry_run_draft_mode_false(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows draft mode is False when set."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("draft", False)
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "Draft Mode: False" in captured.out

    def test_dry_run_draft_mode_bool_true(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with draft=True boolean."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("draft", True)
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "Draft Mode: True" in captured.out

    def test_dry_run_draft_mode_string_true(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with draft='true' string."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("draft", "true")
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "Draft Mode: True" in captured.out

    def test_dry_run_draft_mode_string_no(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with draft='no' string."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("draft", "no")
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "Draft Mode: False" in captured.out

    def test_dry_run_draft_mode_string_0(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run with draft='0' string."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("draft", "0")
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "Draft Mode: False" in captured.out

    def test_dry_run_converts_title(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run converts Markdown title."""
        state.set_value("source_branch", "feature/test")
        state.set_value(
            "title",
            "feature([DFLY-1234](https://jira.swica.ch/browse/DFLY-1234)): test",

        )
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        # Title should have Markdown links stripped
        assert "Title: feature(DFLY-1234): test" in captured.out

    def test_dry_run_with_description(self, temp_state_dir, clear_state_before, capsys):
        """Test dry run shows description when provided."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("description", "This is a test PR description")
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "Description: This is a test PR description" in captured.out

    def test_missing_source_branch(self, temp_state_dir, clear_state_before):
        """Test exits when source branch is missing."""
        state.set_value("title", "Test PR")
        with pytest.raises(SystemExit):
            azure_devops.create_pull_request()

    def test_missing_title(self, temp_state_dir, clear_state_before):
        """Test exits when title is missing."""
        state.set_value("source_branch", "feature/test")
        with pytest.raises(SystemExit):
            azure_devops.create_pull_request()

    def test_missing_description_ok(self, temp_state_dir, clear_state_before, capsys):
        """Test missing description is OK."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "Description:" not in captured.out  # No description line when empty

class TestCreatePullRequestActualCall:
    """Tests for create_pull_request with mocked subprocess calls."""

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_successful_pr_creation(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test successful PR creation."""
        # Mock az --version check
        mock_version = MagicMock()
        mock_version.returncode = 0

        # Mock extension check
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"

        # Mock pr create
        mock_create = MagicMock()
        mock_create.returncode = 0
        mock_create.stdout = '{"pullRequestId": 999, "repository": {"webUrl": "https://test"}}'

        mock_run.side_effect = [mock_version, mock_ext, mock_create]

        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "999" in captured.out

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_pr_creation_failure(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Test PR creation fails when az command fails."""
        # Mock az --version check
        mock_version = MagicMock()
        mock_version.returncode = 0

        # Mock extension check
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"

        # Mock pr create failure
        mock_create = MagicMock()
        mock_create.returncode = 1
        mock_create.stderr = "PR creation failed: branch not found"

        mock_run.side_effect = [mock_version, mock_ext, mock_create]

        state.set_value("source_branch", "feature/nonexistent")
        state.set_value("title", "Test PR")

        with pytest.raises(SystemExit) as exc_info:
            azure_devops.create_pull_request()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error creating PR" in captured.err

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_pr_creation_with_description(self, mock_run, temp_state_dir, clear_state_before):
        """Test PR creation with description."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_create = MagicMock()
        mock_create.returncode = 0
        mock_create.stdout = '{"pullRequestId": 999, "repository": {}}'

        mock_run.side_effect = [mock_version, mock_ext, mock_create]

        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("description", "PR description")

        azure_devops.create_pull_request()

        # Check that description was in the command
        create_call = mock_run.call_args_list[2]
        cmd = create_call[0][0]
        assert "--description" in cmd
