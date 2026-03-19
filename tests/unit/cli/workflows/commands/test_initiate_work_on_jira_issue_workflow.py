"""Tests for initiate_work_on_jira_issue_workflow."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import commands
from agentic_devtools.prompts import loader


@pytest.fixture
def temp_prompts_dir(tmp_path):
    """Create a temporary prompts directory with test templates."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    with patch.object(loader, "get_prompts_dir", return_value=prompts_dir):
        yield prompts_dir


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "temp"
    output_dir.mkdir()
    with patch.object(loader, "get_temp_output_dir", return_value=output_dir):
        yield output_dir


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test.

    Note: We only remove the state file, not the entire temp folder,
    to avoid deleting directories created by other fixtures (like temp_prompts_dir).
    """
    state_file = temp_state_dir / "state.json"
    if state_file.exists():
        state_file.unlink()
    yield


@pytest.fixture
def mock_workflow_state_clearing():
    """Mock clear_state_for_workflow_initiation and _ensure_bootstrap_identity to be no-ops.

    Workflow initiation commands resolve bootstrap identity and reset workflow
    tracking keys (workflow, agdt_run_id) at the start.  This fixture prevents
    both operations, which is useful when tests pre-set workflow state before
    calling the command and want to avoid real filesystem/git operations.
    """
    with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
        with patch("agentic_devtools.cli.workflows.commands._ensure_bootstrap_identity"):
            with patch("agentic_devtools.cli.workflows.commands._ensure_bootstrap_identity_and_scope"):
                yield


class TestInitiateWorkOnJiraIssueInteractive:
    """Tests for the --interactive flag and auto_execute_command behaviour."""

    def test_interactive_true_parsed_from_cli(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that --interactive true enables interactive mode."""
        state.set_value("jira.issue_key", "DFLY-1234")

        with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="DFLY-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_work_on_jira_issue_workflow(_argv=["--interactive", "true"])

        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["interactive"] is True

    def test_interactive_defaults_to_false(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that interactive defaults to False when not specified."""
        state.set_value("jira.issue_key", "DFLY-1234")

        with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="DFLY-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_work_on_jira_issue_workflow(_argv=[])

        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["interactive"] is False

    def test_issue_key_parsed_from_cli(self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys):
        """Test that --issue-key from CLI overrides when not set programmatically."""
        # Don't set issue_key in state — the CLI arg should populate it
        with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="DFLY-5555",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_work_on_jira_issue_workflow(_argv=["--issue-key", "DFLY-5555"])

        # Verify the preflight was called with the CLI-provided issue key
        mock_preflight.assert_called_once_with("DFLY-5555")

    def test_whitespace_only_issue_key_from_cli_fails_fast(
        self,
        temp_state_dir,
        clear_state_before,
        capsys,
    ):
        """Whitespace-only --issue-key should fail with a clear CLI validation error."""
        with pytest.raises(SystemExit):
            commands.initiate_work_on_jira_issue_workflow(_argv=["--issue-key", "   "])

        captured = capsys.readouterr()
        assert "--issue-key cannot be empty or whitespace-only" in captured.err

    def test_auto_execute_command_includes_interactive_flag(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that auto_execute_command includes --interactive."""
        state.set_value("jira.issue_key", "DFLY-1234")

        with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="DFLY-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_work_on_jira_issue_workflow(_argv=["--interactive", "true"])

        call_kwargs = mock_setup.call_args[1]
        expected_cmd = [
            "agdt-initiate-work-on-jira-issue-workflow",
            "--issue-key",
            "DFLY-1234",
            "--interactive",
            "true",
        ]
        assert call_kwargs["auto_execute_command"] == expected_cmd


class TestWorkflowCommands:
    """Tests for individual workflow command functions."""

    def test_work_on_jira_issue_workflow_preflight_fail(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test work on jira issue workflow command when pre-flight fails triggers auto-setup."""
        # Setup state
        state.set_value("jira.issue_key", "DFLY-1234")

        # Mock pre-flight to fail (folder doesn't contain issue key)
        # Patch at commands module level where it's imported at top
        with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong-folder",
                branch_name="main",
                issue_key="DFLY-1234",
            )

            # Mock perform_auto_setup to prevent actual worktree creation
            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_auto_setup:
                mock_auto_setup.return_value = True  # Setup successful

                # Execute command
                commands.initiate_work_on_jira_issue_workflow(_argv=[])

        # Verify - auto-setup was called and workflow returns for continuation in new VS Code
        mock_auto_setup.assert_called_once()
        captured = capsys.readouterr()
        assert "Not in the correct context" in captured.out
        assert "Copilot session will start automatically" in captured.out

    def test_work_on_jira_issue_workflow_preflight_pass(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test work on jira issue workflow command when pre-flight passes."""
        # Setup template for planning step in workflow subfolder
        workflow_dir = temp_prompts_dir / "work-on-jira-issue"
        workflow_dir.mkdir()
        template = "Planning work for {{issue_key}}: {{issue_summary}}"
        template_file = workflow_dir / "default-planning-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Setup state
        state.set_value("jira.issue_key", "DFLY-1234")
        # Mock the issue data that would be fetched
        state.set_value(
            "jira.last_issue",
            {
                "fields": {
                    "summary": "Test issue",
                    "issuetype": {"name": "Task"},
                    "labels": ["backend"],
                    "description": "Test description",
                    "comment": {"comments": []},
                }
            },
        )

        # Mock pre-flight to pass (patch at commands module level where it's imported at top)
        with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="DFLY-1234",
                branch_name="feature/DFLY-1234/test",
                issue_key="DFLY-1234",
            )

            # Also mock perform_auto_setup to prevent any actual subprocess calls
            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_auto_setup:
                mock_auto_setup.return_value = True

                # Mock Jira retrieval to avoid external calls while keeping
                # subprocess behavior intact for identity/bootstrap logic.
                with patch("agentic_devtools.cli.jira.get_commands.get_issue"):
                    # Mock session launcher to avoid waiting for prompt file
                    with patch(
                        "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_work_on_jira_issue"
                    ):
                        # Execute command
                        commands.initiate_work_on_jira_issue_workflow(_argv=[])

        # Verify - should be in planning step
        workflow = state.get_workflow_state()
        assert workflow["active"] == "work-on-jira-issue"
        assert workflow["step"] == "planning"
        captured = capsys.readouterr()
        assert "Planning work for DFLY-1234" in captured.out

    def test_whitespace_only_issue_key_in_state_fails_validation(
        self,
        temp_state_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Whitespace-only jira.issue_key in state is treated as invalid input."""
        state.set_value("jira.issue_key", "   ")

        with pytest.raises(SystemExit):
            commands.initiate_work_on_jira_issue_workflow(_argv=[])

        captured = capsys.readouterr()
        assert "jira.issue_key cannot be empty or whitespace-only" in captured.err
