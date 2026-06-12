"""Tests for create_pull_request function."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import azure_devops


@pytest.fixture(autouse=True)
def _mock_resolve_pr_body():
    """Mock resolve_pr_body for create_pull_request tests.

    The function is called internally by create_pull_request; these tests
    focus on the Azure DevOps CLI interaction, not template resolution.
    Returns the state ``description`` value to preserve existing test semantics.
    """
    with patch(
        "agentic_devtools.cli.pr_template.resolve_pr_body",
    ) as mock:

        def _from_state():
            return state.get_value("description") or ""

        mock.side_effect = _from_state
        yield mock


@pytest.fixture(autouse=True)
def _mock_resolve_pr_title():
    """Mock resolve_pr_title for create_pull_request tests.

    The function is called internally by create_pull_request; these tests
    focus on the Azure DevOps CLI interaction, not title template resolution.
    Returns None so that the fallback (convert_to_pull_request_title) is used.
    """
    with patch(
        "agentic_devtools.cli.pr_template.resolve_pr_title",
        return_value=None,
    ):
        yield


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
            "feature([PROJECT-1234](https://jira.swica.ch/browse/PROJECT-1234)): test",
        )
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        # Title should have Markdown links stripped
        assert "Title: feature(PROJECT-1234): test" in captured.out

    @patch("agentic_devtools.cli.pr_template.resolve_pr_title", return_value="feat(PROJ-99): rendered title")
    def test_dry_run_uses_rendered_title_from_template(self, _mock_title, temp_state_dir, clear_state_before, capsys):
        """Uses rendered title from template when available."""
        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Original Title With [Links](http://x)")
        state.set_dry_run(True)

        azure_devops.create_pull_request()

        captured = capsys.readouterr()
        assert "Title: feat(PROJ-99): rendered title" in captured.out

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

        # On non-Windows platforms, description is passed directly.
        create_call = mock_run.call_args_list[2]
        cmd = create_call[0][0]
        assert "--description" in cmd
        desc_index = cmd.index("--description")
        assert cmd[desc_index + 1] == "PR description"

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_pr_creation_with_draft_false_omits_draft_flag(self, mock_run, temp_state_dir, clear_state_before):
        """A non-draft PR should omit the --draft flag."""
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
        state.set_value("draft", False)

        azure_devops.create_pull_request()

        create_call = mock_run.call_args_list[2]
        cmd = create_call[0][0]
        assert "--draft" not in cmd

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    def test_pr_creation_without_pr_id_does_not_save_state(self, mock_run, temp_state_dir, clear_state_before, capsys):
        """Responses without a PR ID should not persist pull_request_id state."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_create = MagicMock()
        mock_create.returncode = 0
        mock_create.stdout = '{"repository": {"webUrl": "https://test"}}'

        mock_run.side_effect = [mock_version, mock_ext, mock_create]

        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")

        azure_devops.create_pull_request()

        assert state.get_value("pull_request_id") is None
        captured = capsys.readouterr()
        assert "saved to state" not in captured.out

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("subprocess.run")
    @patch("agentic_devtools.cli.pr_template.resolve_pr_body", return_value="Body from template")
    def test_resolve_pr_body_called_and_passed_to_az(self, mock_resolve, mock_run, temp_state_dir, clear_state_before):
        """resolve_pr_body() is invoked and its return value is passed as --description to az."""
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

        azure_devops.create_pull_request()

        mock_resolve.assert_called_once()
        create_call = mock_run.call_args_list[2]
        cmd = create_call[0][0]
        assert "--description" in cmd
        desc_index = cmd.index("--description")
        assert cmd[desc_index + 1] == "Body from template"

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("agentic_devtools.cli.azure_devops.commands.sys.platform", "win32")
    @patch("tempfile.NamedTemporaryFile")
    @patch("os.unlink")
    @patch("subprocess.run")
    def test_pr_creation_with_description_uses_tempfile_on_windows(
        self,
        mock_run,
        mock_unlink,
        mock_named_temporary_file,
        temp_state_dir,
        clear_state_before,
    ):
        """Windows uses @filepath workaround for multiline-safe PR descriptions."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_create = MagicMock()
        mock_create.returncode = 0
        mock_create.stdout = '{"pullRequestId": 999, "repository": {}}'
        mock_run.side_effect = [mock_version, mock_ext, mock_create]

        mock_temp_file = MagicMock()
        mock_temp_file.name = r"C:\temp\agdt-pr-desc.md"
        mock_named_temporary_file.return_value.__enter__.return_value = mock_temp_file

        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("description", "line one\nline two")

        azure_devops.create_pull_request()

        create_call = mock_run.call_args_list[2]
        cmd = create_call[0][0]
        desc_index = cmd.index("--description")
        assert cmd[desc_index + 1] == r"@C:\temp\agdt-pr-desc.md"
        mock_temp_file.write.assert_called_once_with("line one\nline two")
        mock_unlink.assert_called_once_with(r"C:\temp\agdt-pr-desc.md")

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("agentic_devtools.cli.azure_devops.commands.sys.platform", "win32")
    @patch("tempfile.NamedTemporaryFile")
    @patch("os.unlink")
    @patch("subprocess.run")
    def test_pr_creation_escapes_cmd_visible_values_on_windows(
        self,
        mock_run,
        mock_unlink,
        mock_named_temporary_file,
        temp_state_dir,
        clear_state_before,
    ):
        """Windows escapes percent signs in all cmd.exe-visible az arguments."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_create = MagicMock()
        mock_create.returncode = 0
        mock_create.stdout = '{"pullRequestId": 999, "repository": {}}'
        mock_run.side_effect = [mock_version, mock_ext, mock_create]

        mock_temp_file = MagicMock()
        mock_temp_file.name = r"C:\temp\%USERNAME%\agdt-pr-desc.md"
        mock_named_temporary_file.return_value.__enter__.return_value = mock_temp_file

        state.set_value("source_branch", "feature/%USERPROFILE%/test")
        state.set_value("target_branch", "release/%APPDATA%")
        state.set_value("title", "Test %AZURE_DEVOPS_EXT_PAT%")
        state.set_value("description", "line one\nline two")
        state.set_value("organization", "https://dev.azure.com/%ORG%")
        state.set_value("project", "%PROJECT%")
        state.set_value("repository", "%REPO%")

        azure_devops.create_pull_request()

        create_call = mock_run.call_args_list[2]
        cmd = create_call[0][0]

        source_index = cmd.index("--source-branch")
        target_index = cmd.index("--target-branch")
        title_index = cmd.index("--title")
        org_index = cmd.index("--organization")
        project_index = cmd.index("--project")
        repo_index = cmd.index("--repository")
        desc_index = cmd.index("--description")

        assert cmd[source_index + 1] == "feature/%%USERPROFILE%%/test"
        assert cmd[target_index + 1] == "release/%%APPDATA%%"
        assert cmd[title_index + 1] == "Test %%AZURE_DEVOPS_EXT_PAT%%"
        assert cmd[org_index + 1] == "https://dev.azure.com/%%ORG%%"
        assert cmd[project_index + 1] == "%%PROJECT%%"
        assert cmd[repo_index + 1] == "%%REPO%%"
        assert cmd[desc_index + 1] == r"@C:\temp\%%USERNAME%%\agdt-pr-desc.md"
        mock_unlink.assert_called_once_with(r"C:\temp\%USERNAME%\agdt-pr-desc.md")

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("agentic_devtools.cli.azure_devops.commands.sys.platform", "win32")
    @patch("tempfile.NamedTemporaryFile")
    @patch("os.unlink")
    @patch("subprocess.run")
    def test_pr_creation_failure_cleans_up_tempfile_on_windows(
        self,
        mock_run,
        mock_unlink,
        mock_named_temporary_file,
        temp_state_dir,
        clear_state_before,
    ):
        """Windows temp description files are removed even when PR creation fails."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_ext = MagicMock()
        mock_ext.returncode = 0
        mock_ext.stdout = "azure-devops"
        mock_create = MagicMock()
        mock_create.returncode = 1
        mock_create.stderr = "creation failed"
        mock_run.side_effect = [mock_version, mock_ext, mock_create]

        mock_temp_file = MagicMock()
        mock_temp_file.name = r"C:\temp\agdt-pr-desc.md"
        mock_named_temporary_file.return_value.__enter__.return_value = mock_temp_file

        state.set_value("source_branch", "feature/test")
        state.set_value("title", "Test PR")
        state.set_value("description", "line one\nline two")

        with pytest.raises(SystemExit):
            azure_devops.create_pull_request()

        mock_unlink.assert_called_once_with(r"C:\temp\agdt-pr-desc.md")

    @patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"})
    @patch("agentic_devtools.cli.azure_devops.commands.sys.platform", "win32")
    @patch("tempfile.NamedTemporaryFile")
    @patch("subprocess.run")
    def test_pr_creation_without_description_does_not_use_tempfile_on_windows(
        self,
        mock_run,
        mock_named_temporary_file,
        temp_state_dir,
        clear_state_before,
    ):
        """Windows should not create a temp file when description is empty."""
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

        azure_devops.create_pull_request()

        create_call = mock_run.call_args_list[2]
        cmd = create_call[0][0]
        assert "--description" not in cmd
        mock_named_temporary_file.assert_not_called()
