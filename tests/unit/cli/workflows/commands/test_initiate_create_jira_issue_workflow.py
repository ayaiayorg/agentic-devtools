"""Tests for TestInitiateCreateJiraIssueWorkflowBranches."""

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


class TestInitiateCreateJiraIssueWorkflowBranches:
    """Test additional branches in initiate_create_jira_issue_workflow."""

    def test_resolved_issue_key_is_persisted_when_missing_from_current_state_dir(
        self,
        mock_workflow_state_clearing,
    ):
        """Test that a resolved issue key is re-persisted when current state lookup returns None."""
        issue_key_reads = iter(["PROJECT-1234", None])

        def fake_get_value(key, *args, **kwargs):
            if key == "jira.issue_key":
                return next(issue_key_reads)
            if key == "jira.project_key":
                return "PROJECT"
            return None

        with patch("agentic_devtools.state.get_value", side_effect=fake_get_value) as mock_get_value:
            with patch("agentic_devtools.state.set_value") as mock_set_value:
                with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
                    from agentic_devtools.cli.workflows.preflight import PreflightResult

                    mock_pf.return_value = PreflightResult(
                        folder_valid=False,
                        branch_valid=False,
                        folder_name="wrong",
                        branch_name="main",
                        issue_key="PROJECT-1234",
                    )

                    with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup", return_value=True):
                        commands.initiate_create_jira_issue_workflow(_argv=[])

        assert mock_get_value.call_count >= 3
        assert ("jira.issue_key", "PROJECT-1234") in [call.args for call in mock_set_value.call_args_list]

    def test_preflight_fails_and_auto_setup_succeeds(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails but auto-setup succeeds (returns early)."""
        state.set_value("jira.issue_key", "PROJECT-1234")
        state.set_value("jira.project_key", "PROJECT")
        state.set_value("jira.user_request", "I need a story for login")
        state.set_value("jira.issue_type", "Task")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_issue_workflow(_argv=["--issue-key", "PROJECT-1234"])

        captured = capsys.readouterr()
        assert "Not in the correct context" in captured.out
        assert "Copilot session will start automatically" in captured.out

        # Verify auto_execute_command includes --project-key, --user-request, --issue-type
        call_kwargs = mock_setup.call_args[1]
        auto_cmd = call_kwargs["auto_execute_command"]
        assert "--project-key" in auto_cmd
        assert "PROJECT" in auto_cmd
        assert "--user-request" in auto_cmd
        assert "I need a story for login" in auto_cmd
        assert "--issue-type" in auto_cmd
        assert "Task" in auto_cmd
        assert "--skip-copilot-session" in auto_cmd

    def test_model_parsed_from_cli(self, temp_state_dir, clear_state_before, capsys):
        """--model CLI arg overrides the default model."""
        state.set_value("jira.issue_key", "PROJECT-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_issue_workflow(_argv=["--issue-key", "PROJECT-1234", "--model", "gpt-4"])

        assert state.get_value("copilot.model_id") == "gpt-4"

    def test_default_project_key_persisted_to_state(self, temp_state_dir, clear_state_before, capsys):
        """Test that the default project key is persisted to state when not explicitly set."""
        state.set_value("jira.issue_key", "PROJECT-1234")
        # Deliberately NOT setting jira.project_key — the command should persist the default "PROJECT"

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_issue_workflow(_argv=["--issue-key", "PROJECT-1234"])

        # The default "PROJECT" should now be in state
        assert state.get_value("jira.project_key") == "PROJECT"

    def test_preflight_fails_and_auto_setup_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails and auto-setup also fails."""
        state.set_value("jira.issue_key", "PROJECT-1234")
        state.set_value("jira.project_key", "PROJECT")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = False
                with pytest.raises(SystemExit) as exc_info:
                    commands.initiate_create_jira_issue_workflow(_argv=["--issue-key", "PROJECT-1234"])
                assert exc_info.value.code == 1

    def test_no_issue_key_creates_placeholder(self, temp_state_dir, clear_state_before, capsys):
        """Test when no issue_key provided, calls create_placeholder_and_setup_worktree."""
        state.set_value("jira.project_key", "PROJECT")

        with patch(
            "agentic_devtools.cli.workflows.worktree_setup.create_placeholder_and_setup_worktree"
        ) as mock_create:
            mock_create.return_value = (True, "PROJECT-9999")
            commands.initiate_create_jira_issue_workflow(_argv=[])

        mock_create.assert_called_once()
        captured = capsys.readouterr()
        assert "Copilot session will start automatically" in captured.out

    def test_no_issue_key_placeholder_creation_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test when placeholder creation fails."""
        state.set_value("jira.project_key", "PROJECT")

        with patch(
            "agentic_devtools.cli.workflows.worktree_setup.create_placeholder_and_setup_worktree"
        ) as mock_create:
            mock_create.return_value = (False, None)
            with pytest.raises(SystemExit) as exc_info:
                commands.initiate_create_jira_issue_workflow(_argv=[])
            assert exc_info.value.code == 1


class TestInitiateCreateJiraIssueInteractive:
    """Tests for the --interactive flag behaviour."""

    def test_interactive_true_parsed_from_cli(self, temp_state_dir, clear_state_before, capsys):
        """Test that --interactive true enables interactive mode."""
        state.set_value("jira.issue_key", "PROJECT-1234")
        state.set_value("jira.project_key", "PROJECT")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_issue_workflow(
                    _argv=["--issue-key", "PROJECT-1234", "--interactive", "true"]
                )

        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["interactive"] is True

    def test_interactive_defaults_to_false(self, temp_state_dir, clear_state_before, capsys):
        """Test that interactive defaults to False when not specified."""
        state.set_value("jira.issue_key", "PROJECT-1234")
        state.set_value("jira.project_key", "PROJECT")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_issue_workflow(_argv=["--issue-key", "PROJECT-1234"])

        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["interactive"] is False


class TestWorkflowCommands:
    """Tests for individual workflow command functions."""

    def test_create_jira_issue_workflow(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test create jira issue workflow command with continuation (issue key already provided)."""
        # Setup template in workflow subfolder
        workflow_dir = temp_prompts_dir / "create-jira-issue"
        workflow_dir.mkdir()
        template = "Creating issue in {{jira_project_key}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Setup state - simulate continuation after placeholder creation
        state.set_value("jira.project_key", "PROJECT")
        state.set_value("jira.issue_key", "PROJECT-1234")  # Provided issue key means continuation

        # Mock preflight to pass (we're already in correct context)
        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="PROJECT-1234",
                branch_name="feature/PROJECT-1234/implementation",
                issue_key="PROJECT-1234",
            )

            # Mock session launcher to avoid waiting for prompt file
            with patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_create_jira_issue"):
                # Execute command with issue-key (continuation mode)
                commands.initiate_create_jira_issue_workflow(_argv=["--issue-key", "PROJECT-1234"])

        # Verify
        workflow = state.get_workflow_state()
        assert workflow["active"] == "create-jira-issue"


class TestSkipCopilotSession:
    """Tests for the --skip-copilot-session flag."""

    def _run_with_preflight_passing(self, issue_key, argv=None, skip_copilot_session=False):
        """Helper: run the command with preflight passing, return mock_session."""
        from agentic_devtools.cli.workflows.preflight import PreflightResult

        argv = argv or []
        state.set_value("jira.issue_key", issue_key)
        state.set_value("jira.project_key", "PROJECT")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_preflight:
            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name=issue_key,
                branch_name=f"feature/{issue_key}/implementation",
                issue_key=issue_key,
            )
            with patch(
                "agentic_devtools.cli.workflows.commands.get_git_repo_root",
                return_value="/fake/repo-root",
            ):
                with patch("agentic_devtools.cli.workflows.commands.initiate_workflow"):
                    with patch(
                        "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_create_jira_issue"
                    ) as mock_session:
                        with patch(
                            "agentic_devtools.cli.workflows.commands.get_default_copilot_model",
                            return_value="gpt-4o",
                        ):
                            commands.initiate_create_jira_issue_workflow(
                                _argv=["--issue-key", issue_key] + argv,
                                skip_copilot_session=skip_copilot_session,
                            )
                            return mock_session

    def test_skip_copilot_session_programmatic(self, temp_state_dir, clear_state_before, mock_workflow_state_clearing):
        """skip_copilot_session=True prevents copilot session from starting."""
        mock_session = self._run_with_preflight_passing("PROJECT-1234", skip_copilot_session=True)
        mock_session.assert_not_called()

    def test_skip_copilot_session_cli_flag(self, temp_state_dir, clear_state_before, mock_workflow_state_clearing):
        """--skip-copilot-session CLI flag prevents copilot session from starting."""
        mock_session = self._run_with_preflight_passing("PROJECT-1234", argv=["--skip-copilot-session"])
        mock_session.assert_not_called()
