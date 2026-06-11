"""Tests for TestInitiateCreateJiraSubtaskWorkflowBranches."""

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


class TestInitiateCreateJiraSubtaskWorkflowBranches:
    """Test additional branches in initiate_create_jira_subtask_workflow."""

    def test_preflight_fails_and_auto_setup_succeeds(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails but auto-setup succeeds (returns early)."""
        state.set_value("jira.issue_key", "PROJECT-1235")
        state.set_value("jira.parent_key", "PROJECT-1234")
        state.set_value("jira.user_request", "I need a subtask for testing")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1235",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_subtask_workflow(_argv=["--issue-key", "PROJECT-1235"])

        captured = capsys.readouterr()
        assert "Not in the correct context" in captured.out
        assert "Copilot session will start automatically" in captured.out

        # Verify auto_execute_command includes --parent-key and --user-request
        call_kwargs = mock_setup.call_args[1]
        auto_cmd = call_kwargs["auto_execute_command"]
        assert "--parent-key" in auto_cmd
        assert "PROJECT-1234" in auto_cmd
        assert "--user-request" in auto_cmd
        assert "I need a subtask for testing" in auto_cmd
        assert "--skip-copilot-session" in auto_cmd

    def test_model_parsed_from_cli(self, temp_state_dir, clear_state_before, capsys):
        """--model CLI arg overrides the default model."""
        state.set_value("jira.issue_key", "PROJECT-1235")
        state.set_value("jira.parent_key", "PROJECT-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1235",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_subtask_workflow(
                    _argv=["--issue-key", "PROJECT-1235", "--model", "gpt-4"]
                )

        assert state.get_value("copilot.model_id") == "gpt-4"

    def test_preflight_fails_and_auto_setup_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails and auto-setup also fails."""
        state.set_value("jira.issue_key", "PROJECT-1235")
        state.set_value("jira.parent_key", "PROJECT-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1235",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = False
                with pytest.raises(SystemExit) as exc_info:
                    commands.initiate_create_jira_subtask_workflow(_argv=["--issue-key", "PROJECT-1235"])
                assert exc_info.value.code == 1

    def test_preflight_fails_without_parent_key_exits(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails and parent_key is missing, exits with error."""
        state.set_value("jira.issue_key", "PROJECT-1235")
        # No jira.parent_key set

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1235",
            )

            with pytest.raises(SystemExit) as exc_info:
                commands.initiate_create_jira_subtask_workflow(_argv=["--issue-key", "PROJECT-1235"])
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "--parent-key is required" in captured.out

    def test_no_issue_key_no_parent_key_error(self, temp_state_dir, clear_state_before, capsys):
        """Test when no issue_key and no parent_key, shows error."""
        with pytest.raises(SystemExit) as exc_info:
            commands.initiate_create_jira_subtask_workflow(_argv=[])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--parent-key is required" in captured.out

    def test_no_issue_key_creates_placeholder(self, temp_state_dir, clear_state_before, capsys):
        """Test when no issue_key but parent_key provided, creates placeholder and auto-setup."""
        state.set_value("jira.parent_key", "PROJECT-1234")

        from agentic_devtools.cli.workflows.worktree_setup import PlaceholderIssueResult

        with patch("agentic_devtools.cli.workflows.worktree_setup.create_placeholder_issue") as mock_create:
            mock_create.return_value = PlaceholderIssueResult(success=True, issue_key="PROJECT-1235")
            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_subtask_workflow(_argv=["--parent-key", "PROJECT-1234"])

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["issue_type"] == "Sub-task"
        assert call_kwargs["parent_key"] == "PROJECT-1234"
        mock_setup.assert_called_once()
        setup_kwargs = mock_setup.call_args[1]
        setup_args = mock_setup.call_args[0]
        assert setup_args[1] == "update-jira-issue"
        assert setup_kwargs["auto_execute_command"][0] == "agdt-initiate-update-jira-issue-workflow"
        assert "PROJECT-1235" in setup_kwargs["auto_execute_command"]
        captured = capsys.readouterr()
        assert "Copilot session will start automatically" in captured.out

    def test_no_issue_key_no_additional_params_for_update_workflow(self, temp_state_dir, clear_state_before, capsys):
        """The update-jira-issue workflow does not accept --parent-key, so additional_params
        must be None (or absent) when perform_auto_setup targets update-jira-issue."""
        state.set_value("jira.parent_key", "PROJECT-1234")

        from agentic_devtools.cli.workflows.worktree_setup import PlaceholderIssueResult

        with patch("agentic_devtools.cli.workflows.worktree_setup.create_placeholder_issue") as mock_create:
            mock_create.return_value = PlaceholderIssueResult(success=True, issue_key="PROJECT-1235")
            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_subtask_workflow(_argv=["--parent-key", "PROJECT-1234"])

        setup_kwargs = mock_setup.call_args[1]
        # additional_params must not contain parent_key — update-jira-issue doesn't accept --parent-key
        additional_params = setup_kwargs.get("additional_params")
        assert additional_params is None or "parent_key" not in additional_params

    def test_no_issue_key_no_user_request_does_not_inject_none(self, temp_state_dir, clear_state_before, capsys):
        """When no user_request is provided, 'None' must not appear in the update_user_request."""
        state.set_value("jira.parent_key", "PROJECT-1234")

        from agentic_devtools.cli.workflows.worktree_setup import PlaceholderIssueResult

        with patch("agentic_devtools.cli.workflows.worktree_setup.create_placeholder_issue") as mock_create:
            mock_create.return_value = PlaceholderIssueResult(success=True, issue_key="PROJECT-1235")
            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_subtask_workflow(_argv=["--parent-key", "PROJECT-1234"])

        call_kwargs = mock_setup.call_args[1]
        assert "None" not in call_kwargs["user_request"]
        assert "None" not in " ".join(call_kwargs["auto_execute_command"])

    def test_no_issue_key_user_request_propagated_consistently(self, temp_state_dir, clear_state_before, capsys):
        """The user_request kwarg to perform_auto_setup must match what's in auto_execute_command."""
        state.set_value("jira.parent_key", "PROJECT-1234")

        from agentic_devtools.cli.workflows.worktree_setup import PlaceholderIssueResult

        with patch("agentic_devtools.cli.workflows.worktree_setup.create_placeholder_issue") as mock_create:
            mock_create.return_value = PlaceholderIssueResult(success=True, issue_key="PROJECT-1235")
            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_subtask_workflow(
                    _argv=["--parent-key", "PROJECT-1234", "--user-request", "Add unit tests"]
                )

        call_kwargs = mock_setup.call_args[1]
        auto_cmd = call_kwargs["auto_execute_command"]
        user_request_kwarg = call_kwargs["user_request"]
        ur_idx = auto_cmd.index("--user-request") + 1
        assert auto_cmd[ur_idx] == user_request_kwarg
        assert "Add unit tests" in user_request_kwarg

    def test_no_issue_key_placeholder_creation_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test when placeholder creation fails."""
        state.set_value("jira.parent_key", "PROJECT-1234")

        from agentic_devtools.cli.workflows.worktree_setup import PlaceholderIssueResult

        with patch("agentic_devtools.cli.workflows.worktree_setup.create_placeholder_issue") as mock_create:
            mock_create.return_value = PlaceholderIssueResult(success=False, error_message="API error")
            with pytest.raises(SystemExit) as exc_info:
                commands.initiate_create_jira_subtask_workflow(_argv=["--parent-key", "PROJECT-1234"])
            assert exc_info.value.code == 1

    def test_no_issue_key_auto_setup_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test when placeholder succeeds but perform_auto_setup fails."""
        state.set_value("jira.parent_key", "PROJECT-1234")

        from agentic_devtools.cli.workflows.worktree_setup import PlaceholderIssueResult

        with patch("agentic_devtools.cli.workflows.worktree_setup.create_placeholder_issue") as mock_create:
            mock_create.return_value = PlaceholderIssueResult(success=True, issue_key="PROJECT-1235")
            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = False
                with pytest.raises(SystemExit) as exc_info:
                    commands.initiate_create_jira_subtask_workflow(_argv=["--parent-key", "PROJECT-1234"])
                assert exc_info.value.code == 1


class TestProgrammaticParamsSkipCliOverride:
    """Tests that programmatic params skip the CLI arg override branches."""

    def test_all_params_set_programmatically(self, temp_state_dir, clear_state_before, capsys):
        """When parent_key, issue_key, user_request are all set
        programmatically, the `if X is None:` CLI override branches are skipped."""
        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJ-2",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_subtask_workflow(
                    parent_key="PROJ-1",
                    issue_key="PROJ-2",
                    user_request="Add unit tests",
                )

        call_kwargs = mock_setup.call_args[1]
        auto_cmd = call_kwargs["auto_execute_command"]
        assert "--parent-key" in auto_cmd
        assert "PROJ-1" in auto_cmd
        assert "--user-request" in auto_cmd
        assert "Add unit tests" in auto_cmd


class TestInitiateCreateJiraSubtaskInteractive:
    """Tests for the --interactive flag behaviour."""

    def test_interactive_true_parsed_from_cli(self, temp_state_dir, clear_state_before, capsys):
        """Test that --interactive true enables interactive mode."""
        state.set_value("jira.issue_key", "PROJECT-1235")
        state.set_value("jira.parent_key", "PROJECT-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1235",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_subtask_workflow(
                    _argv=["--issue-key", "PROJECT-1235", "--interactive", "true"]
                )

        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["interactive"] is True

    def test_interactive_defaults_to_false(self, temp_state_dir, clear_state_before, capsys):
        """Test that interactive defaults to False when not specified."""
        state.set_value("jira.issue_key", "PROJECT-1235")
        state.set_value("jira.parent_key", "PROJECT-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1235",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_subtask_workflow(_argv=["--issue-key", "PROJECT-1235"])

        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["interactive"] is False


class TestWorkflowCommands:
    """Tests for individual workflow command functions."""

    def test_create_jira_subtask_workflow(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test create jira subtask workflow command with continuation (issue key already provided)."""
        # Setup template in workflow subfolder
        workflow_dir = temp_prompts_dir / "create-jira-subtask"
        workflow_dir.mkdir()
        template = "Creating subtask for {{jira_parent_key}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Setup state - simulate continuation after placeholder creation
        state.set_value("jira.parent_key", "PROJECT-1234")
        state.set_value("jira.issue_key", "PROJECT-1235")  # Provided issue key means continuation

        # Mock preflight to pass (we're already in correct context)
        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="PROJECT-1235",
                branch_name="feature/PROJECT-1234/PROJECT-1235/implementation",
                issue_key="PROJECT-1235",
            )

            # Mock session launcher to avoid waiting for prompt file
            with patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_create_jira_subtask"):
                # Execute command with issue-key (continuation mode)
                commands.initiate_create_jira_subtask_workflow(_argv=["--issue-key", "PROJECT-1235"])

        # Verify
        workflow = state.get_workflow_state()
        assert workflow["active"] == "create-jira-subtask"


class TestResolvedParentKeyPersist:
    """Tests for the resolved parent key persistence guards in the workflow."""

    def test_resolved_parent_key_is_persisted_to_state(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test that resolved_parent_key is written to state when provided via CLI.

        When --parent-key is passed explicitly, resolved_parent_key is truthy and
        set_value("jira.parent_key", ...) must be called by the workflow implementation.
        """
        from agentic_devtools.cli.workflows.preflight import PreflightResult

        workflow_dir = temp_prompts_dir / "create-jira-subtask"
        workflow_dir.mkdir()
        (workflow_dir / "default-initiate-prompt.md").write_text(
            "Creating subtask for {{jira_parent_key}}", encoding="utf-8"
        )

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            mock_pf.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="PROJECT-1235",
                branch_name="feature/PROJECT-1234/PROJECT-1235/impl",
                issue_key="PROJECT-1235",
            )
            with patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_create_jira_subtask"):
                commands.initiate_create_jira_subtask_workflow(
                    _argv=["--issue-key", "PROJECT-1235", "--parent-key", "PROJECT-1234"]
                )

        assert state.get_value("jira.parent_key") == "PROJECT-1234"

    def test_issue_key_write_guard_triggers_when_current_differs(
        self,
        temp_state_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Guard re-writes jira.issue_key when current state differs from resolved issue key.

        This simulates a bootstrap-missing scenario by mocking state.set_value as a no-op
        so the initial write of jira.issue_key does not persist to state. A subsequent
        get_value therefore returns None, making current_issue_key != resolved_issue_key
        truthy and exercising the guarded set_value path that re-writes jira.issue_key.
        """
        from unittest.mock import call as mock_call

        from agentic_devtools.cli.workflows.preflight import PreflightResult

        with patch("agentic_devtools.state.set_value") as mock_set_value:
            with patch("agentic_devtools.cli.workflows.commands.initiate_workflow"):
                with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
                    mock_pf.return_value = PreflightResult(
                        folder_valid=True,
                        branch_valid=True,
                        folder_name="PROJECT-1235",
                        branch_name="feature/PROJECT-1234/PROJECT-1235/impl",
                        issue_key="PROJECT-1235",
                    )
                    commands.initiate_create_jira_subtask_workflow(
                        _argv=["--issue-key", "PROJECT-1235", "--parent-key", "PROJECT-1234"]
                    )

        # set_value("jira.issue_key", "PROJECT-1235") must be called at least twice:
        # once during the initial persist and once inside the write guard when the
        # current_issue_key read from state differs from the resolved_issue_key.
        issue_key_calls = [c for c in mock_set_value.call_args_list if c == mock_call("jira.issue_key", "PROJECT-1235")]
        assert len(issue_key_calls) >= 2, (
            f"Expected set_value('jira.issue_key', ...) called ≥2 times, got {issue_key_calls}"
        )


class TestSkipCopilotSession:
    """Tests for the --skip-copilot-session flag."""

    def _run_with_preflight_passing(self, issue_key, argv=None, skip_copilot_session=False):
        """Helper: run the command with preflight passing, return mock_session."""
        from agentic_devtools.cli.workflows.preflight import PreflightResult

        argv = argv or []
        state.set_value("jira.issue_key", issue_key)
        state.set_value("jira.parent_key", "PROJECT-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_preflight:
            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name=issue_key,
                branch_name=f"feature/PROJECT-1234/{issue_key}/implementation",
                issue_key=issue_key,
            )
            with patch(
                "agentic_devtools.cli.workflows.commands.get_git_repo_root",
                return_value="/fake/repo-root",
            ):
                with patch("agentic_devtools.cli.workflows.commands.initiate_workflow"):
                    with patch(
                        "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_create_jira_subtask"
                    ) as mock_session:
                        with patch(
                            "agentic_devtools.cli.workflows.commands.get_default_copilot_model",
                            return_value="gpt-4o",
                        ):
                            commands.initiate_create_jira_subtask_workflow(
                                _argv=["--issue-key", issue_key] + argv,
                                skip_copilot_session=skip_copilot_session,
                            )
                            return mock_session

    def test_skip_copilot_session_programmatic(self, temp_state_dir, clear_state_before, mock_workflow_state_clearing):
        """skip_copilot_session=True prevents copilot session from starting."""
        mock_session = self._run_with_preflight_passing("PROJECT-1235", skip_copilot_session=True)
        mock_session.assert_not_called()

    def test_skip_copilot_session_cli_flag(self, temp_state_dir, clear_state_before, mock_workflow_state_clearing):
        """--skip-copilot-session CLI flag prevents copilot session from starting."""
        mock_session = self._run_with_preflight_passing("PROJECT-1235", argv=["--skip-copilot-session"])
        mock_session.assert_not_called()


class TestCreateJiraSubtaskStaleStateClearance:
    """Tests for stale issue key clearing when --issue-key is not provided."""

    def test_stale_jira_issue_key_cleared_when_no_issue_key_arg(self, temp_state_dir, clear_state_before, capsys):
        """Stale jira.issue_key from prior workflow is cleared, create-placeholder path is taken."""
        state.set_value("jira.issue_key", "STALE-999")
        state.set_value("jira.parent_key", "PROJECT-1234")

        from agentic_devtools.cli.workflows.worktree_setup import PlaceholderIssueResult

        with patch("agentic_devtools.cli.workflows.worktree_setup.create_placeholder_issue") as mock_create:

            def _mock_create_placeholder(**_kwargs):
                # Stale key must be cleared before placeholder creation starts.
                assert state.get_value("jira.issue_key") is None
                return PlaceholderIssueResult(success=True, issue_key="PROJECT-NEW-1")

            mock_create.side_effect = _mock_create_placeholder
            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_subtask_workflow(_argv=["--parent-key", "PROJECT-1234"])

        # Stale key was cleared — create path was taken (not the existing-issue path)
        mock_create.assert_called_once()
        assert state.get_value("jira.issue_key") == "PROJECT-NEW-1"

    def test_stale_state_emits_stderr_message(self, temp_state_dir, clear_state_before, capsys):
        """Stderr contains informational message when stale keys are cleared."""
        state.set_value("jira.issue_key", "STALE-999")
        state.set_value("jira.parent_key", "PROJECT-1234")

        from agentic_devtools.cli.workflows.worktree_setup import PlaceholderIssueResult

        with patch("agentic_devtools.cli.workflows.worktree_setup.create_placeholder_issue") as mock_create:
            mock_create.return_value = PlaceholderIssueResult(success=True, issue_key="PROJECT-NEW-1")
            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_subtask_workflow(_argv=["--parent-key", "PROJECT-1234"])

        captured = capsys.readouterr()
        assert "Cleared stale issue selection state" in captured.err

    def test_no_stale_state_no_stderr_message(self, temp_state_dir, clear_state_before, capsys):
        """No stderr message when no stale keys exist."""
        state.set_value("jira.parent_key", "PROJECT-1234")

        from agentic_devtools.cli.workflows.worktree_setup import PlaceholderIssueResult

        with patch("agentic_devtools.cli.workflows.worktree_setup.create_placeholder_issue") as mock_create:
            mock_create.return_value = PlaceholderIssueResult(success=True, issue_key="PROJECT-NEW-1")
            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_subtask_workflow(_argv=["--parent-key", "PROJECT-1234"])

        captured = capsys.readouterr()
        assert "Cleared stale issue selection state" not in captured.err

    def test_explicit_issue_key_preserves_state(self, temp_state_dir, clear_state_before, capsys):
        """Explicit --issue-key bypasses stale-state clearing."""
        state.set_value("jira.issue_key", "PROJECT-1235")
        state.set_value("jira.parent_key", "PROJECT-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1235",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_subtask_workflow(
                    _argv=["--issue-key", "PROJECT-1235", "--parent-key", "PROJECT-1234"]
                )

        # No stale-state warning emitted
        captured = capsys.readouterr()
        assert "Cleared stale issue selection state" not in captured.err
        # Issue key is preserved in state
        assert state.get_value("jira.issue_key") == "PROJECT-1235"

    def test_parent_key_preserved_after_stale_clear(self, temp_state_dir, clear_state_before, capsys):
        """jira.parent_key survives the stale issue key clearing."""
        state.set_value("jira.issue_key", "STALE-999")
        state.set_value("jira.parent_key", "PROJECT-1234")

        from agentic_devtools.cli.workflows.worktree_setup import PlaceholderIssueResult

        with patch("agentic_devtools.cli.workflows.worktree_setup.create_placeholder_issue") as mock_create:
            mock_create.return_value = PlaceholderIssueResult(success=True, issue_key="PROJECT-NEW-1")
            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_subtask_workflow(_argv=["--parent-key", "PROJECT-1234"])

        assert state.get_value("jira.parent_key") == "PROJECT-1234"
