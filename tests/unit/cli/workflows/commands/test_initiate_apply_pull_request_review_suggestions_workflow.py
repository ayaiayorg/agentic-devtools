"""Tests for TestInitiateApplyPRSuggestionsWorkflowBranches."""

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


class TestInitiateApplyPRSuggestionsWorkflowBranches:
    """Test additional branches in initiate_apply_pull_request_review_suggestions_workflow."""

    def test_cli_args_set_pull_request_id_and_issue_key(
        self,
        temp_state_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test that --pull-request-id and --issue-key CLI args are parsed and stored in state."""
        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="DFLY-5678",
                branch_name="feature/DFLY-5678/implementation",
                issue_key="DFLY-5678",
            )

            with patch("agentic_devtools.cli.workflows.commands.initiate_workflow"):
                with patch("agentic_devtools.cli.workflows.commands._copy_review_state_to_apply_suggestions"):
                    with patch(
                        "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_apply_pr_suggestions"
                    ):
                        commands.initiate_apply_pull_request_review_suggestions_workflow(
                            _argv=["--pull-request-id", "456", "--issue-key", "DFLY-5678"]
                        )

        assert state.get_value("pull_request_id") == "456"
        assert state.get_value("jira.issue_key") == "DFLY-5678"

    def test_derives_issue_key_from_pr_details(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test issue key is derived from PR details when not provided."""
        state.set_value("pull_request_id", "123")
        state.set_value(
            "pr_details",
            {"sourceRefName": "refs/heads/feature/DFLY-1234/implementation"},
        )

        workflow_dir = temp_prompts_dir / "apply-pull-request-review-suggestions"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text("Applying suggestions for {{pull_request_id}}", encoding="utf-8")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="DFLY-1234",
                branch_name="feature/DFLY-1234/implementation",
                issue_key="DFLY-1234",
            )

            with patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_apply_pr_suggestions"):
                commands.initiate_apply_pull_request_review_suggestions_workflow(_argv=[])

        assert state.get_value("jira.issue_key") == "DFLY-1234"

    def test_preflight_fails_and_auto_setup_succeeds(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test when preflight fails but auto-setup succeeds (returns early)."""
        state.set_value("pull_request_id", "123")
        state.set_value("jira.issue_key", "DFLY-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="DFLY-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_apply_pull_request_review_suggestions_workflow(_argv=[])

        captured = capsys.readouterr()
        assert "Not in the correct context" in captured.out
        assert "Copilot session will start automatically" in captured.out

    def test_preflight_fails_and_auto_setup_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails and auto-setup also fails."""
        state.set_value("pull_request_id", "123")
        state.set_value("jira.issue_key", "DFLY-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="DFLY-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = False
                with pytest.raises(SystemExit) as exc_info:
                    commands.initiate_apply_pull_request_review_suggestions_workflow(_argv=[])
                assert exc_info.value.code == 1


class TestWorkflowCommands:
    """Tests for individual workflow command functions."""

    def test_apply_pr_suggestions_workflow(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test apply pull request review suggestions workflow command."""
        # Setup template in workflow subfolder
        workflow_dir = temp_prompts_dir / "apply-pull-request-review-suggestions"
        workflow_dir.mkdir()
        template = "Applying suggestions from PR #{{pull_request_id}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Setup state
        state.set_value("pull_request_id", "789")
        state.set_value("jira.issue_key", "DFLY-1234")  # Issue key needed for preflight

        # Mock preflight to pass (we're already in correct context)
        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="DFLY-1234",
                branch_name="feature/DFLY-1234/implementation",
                issue_key="DFLY-1234",
            )

            with patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_apply_pr_suggestions"):
                # Execute command
                commands.initiate_apply_pull_request_review_suggestions_workflow(_argv=[])

        # Verify
        workflow = state.get_workflow_state()
        assert workflow["active"] == "apply-pull-request-review-suggestions"


class TestInitiateApplyPRSuggestionsWorkflowInteractive:
    """Tests for the --interactive flag and auto_execute_command behaviour."""

    def _run_with_preflight_failing(self, argv=None):
        """Helper: run the command with preflight failing, return mock_setup."""
        from agentic_devtools.cli.workflows.preflight import PreflightResult

        argv = argv or []
        state.set_value("pull_request_id", "123")
        state.set_value("jira.issue_key", "DFLY-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="DFLY-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_apply_pull_request_review_suggestions_workflow(_argv=argv)
                return mock_setup

    def test_interactive_flag_false_parsed_from_cli(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that --interactive false results in interactive=False to perform_auto_setup."""
        mock_setup = self._run_with_preflight_failing(argv=["--interactive", "false"])

        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["interactive"] is False

    def test_interactive_flag_true_parsed_from_cli(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that --interactive true passes interactive=True to perform_auto_setup.

        The VS Code auto-start task now uses workflow-specific prompts via
        ``_WORKFLOW_START_PROMPTS``, so interactive mode is passed through.
        """
        mock_setup = self._run_with_preflight_failing(argv=["--interactive", "true"])

        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["interactive"] is True

    def test_interactive_defaults_to_false(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that interactive defaults to False when not specified."""
        mock_setup = self._run_with_preflight_failing(argv=[])

        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["interactive"] is False

    def test_auto_execute_command_includes_interactive_false(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that auto_execute_command includes --interactive false by default."""
        mock_setup = self._run_with_preflight_failing(argv=[])

        call_kwargs = mock_setup.call_args[1]
        auto_cmd = call_kwargs["auto_execute_command"]
        assert "--interactive" in auto_cmd
        interactive_idx = auto_cmd.index("--interactive")
        assert auto_cmd[interactive_idx + 1] == "false"

    def test_auto_execute_command_includes_interactive_true(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that auto_execute_command includes --interactive true when explicitly set."""
        mock_setup = self._run_with_preflight_failing(argv=["--interactive", "true"])

        call_kwargs = mock_setup.call_args[1]
        auto_cmd = call_kwargs["auto_execute_command"]
        assert "--interactive" in auto_cmd
        interactive_idx = auto_cmd.index("--interactive")
        assert auto_cmd[interactive_idx + 1] == "true"

    def test_auto_execute_command_includes_pull_request_id(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that auto_execute_command includes --pull-request-id."""
        mock_setup = self._run_with_preflight_failing(argv=[])

        call_kwargs = mock_setup.call_args[1]
        auto_cmd = call_kwargs["auto_execute_command"]
        assert "--pull-request-id" in auto_cmd
        pr_idx = auto_cmd.index("--pull-request-id")
        assert auto_cmd[pr_idx + 1] == "123"

    def test_auto_execute_command_includes_issue_key(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that auto_execute_command includes --issue-key when available."""
        mock_setup = self._run_with_preflight_failing(argv=[])

        call_kwargs = mock_setup.call_args[1]
        auto_cmd = call_kwargs["auto_execute_command"]
        assert "--issue-key" in auto_cmd
        ik_idx = auto_cmd.index("--issue-key")
        assert auto_cmd[ik_idx + 1] == "DFLY-1234"

    def test_auto_execute_command_starts_with_correct_command(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that auto_execute_command starts with the correct CLI command name."""
        mock_setup = self._run_with_preflight_failing(argv=[])

        call_kwargs = mock_setup.call_args[1]
        auto_cmd = call_kwargs["auto_execute_command"]
        assert auto_cmd[0] == "agdt-initiate-apply-pr-suggestions-workflow"


class TestInitiateApplyPRSuggestionsWorkflowCopilotSession:
    """Tests for the Copilot session started after preflight passes."""

    def _run_with_preflight_passing(self, pr_id, issue_key=None, argv=None):
        """Helper: run the command with preflight passing, return mock_session."""
        from agentic_devtools.cli.workflows.preflight import PreflightResult

        argv = argv or []
        state.set_value("pull_request_id", pr_id)
        if issue_key:
            state.set_value("jira.issue_key", issue_key)

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_preflight:
            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name=issue_key or f"PR{pr_id}",
                branch_name="feature/some-branch",
                issue_key=issue_key,
            )
            with patch(
                "agentic_devtools.cli.workflows.commands.get_git_repo_root",
                return_value="/fake/repo-root",
            ):
                with patch("agentic_devtools.cli.workflows.commands.initiate_workflow"):
                    with patch("agentic_devtools.cli.workflows.commands._copy_review_state_to_apply_suggestions"):
                        with patch(
                            "agentic_devtools.cli.workflows.worktree_setup"
                            "._start_copilot_session_for_apply_pr_suggestions"
                        ) as mock_session:
                            commands.initiate_apply_pull_request_review_suggestions_workflow(_argv=argv)
                            return mock_session

    def test_copilot_session_started_when_preflight_passes(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing
    ):
        """_start_copilot_session_for_apply_pr_suggestions is called with the repo root."""
        mock_session = self._run_with_preflight_passing("999", issue_key="DFLY-9999")
        mock_session.assert_called_once()
        call_args = mock_session.call_args
        assert call_args[0][0] == "/fake/repo-root"

    def test_copilot_session_interactive_default_is_false(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing
    ):
        """_start_copilot_session_for_apply_pr_suggestions is called with interactive=False by default."""
        mock_session = self._run_with_preflight_passing("999", issue_key="DFLY-9999")
        mock_session.assert_called_once_with("/fake/repo-root", interactive=False)

    def test_copilot_session_respects_interactive_false(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing
    ):
        """Session is called with interactive=False when --interactive false."""
        mock_session = self._run_with_preflight_passing("999", issue_key="DFLY-9999", argv=["--interactive", "false"])
        mock_session.assert_called_once_with("/fake/repo-root", interactive=False)

    def test_copilot_session_interactive_true_when_explicitly_set(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing
    ):
        """Session is called with interactive=True when --interactive true."""
        mock_session = self._run_with_preflight_passing("999", issue_key="DFLY-9999", argv=["--interactive", "true"])
        mock_session.assert_called_once_with("/fake/repo-root", interactive=True)


class TestInitiateApplyPRSuggestionsBootstrapScope:
    """Tests that the correct worktree_key scope is set before any set_value() calls."""

    def test_both_pr_id_and_issue_key_uses_issue_key_as_worktree_key(self, temp_state_dir, clear_state_before):
        """When both --pull-request-id and --issue-key are provided, worktree_key is the issue key.

        Issue key takes priority over PR ID, matching resolve_worktree_key() in agdt_branch.py.
        _ensure_bootstrap_identity_and_scope must be called with the issue key BEFORE any
        set_value() calls.
        """
        with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
            with patch("agentic_devtools.cli.workflows.commands._ensure_bootstrap_identity_and_scope") as mock_scope:
                with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
                    from agentic_devtools.cli.workflows.preflight import PreflightResult

                    mock_pf.return_value = PreflightResult(
                        folder_valid=True,
                        branch_valid=True,
                        folder_name="DFLY-2779",
                        branch_name="feature/DFLY-2779/test",
                        issue_key="DFLY-2779",
                    )

                    with patch("agentic_devtools.cli.workflows.commands.initiate_workflow"):
                        with patch("agentic_devtools.cli.workflows.commands._copy_review_state_to_apply_suggestions"):
                            with patch(
                                "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_apply_pr_suggestions"
                            ):
                                commands.initiate_apply_pull_request_review_suggestions_workflow(
                                    _argv=["--pull-request-id", "25858", "--issue-key", "DFLY-2779"]
                                )

        mock_scope.assert_called_once_with("DFLY-2779")

    def test_only_pr_id_uses_pr_worktree_key(self, temp_state_dir, clear_state_before):
        """When only --pull-request-id is provided, worktree_key is PR{id}."""
        with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
            with patch("agentic_devtools.cli.workflows.commands._ensure_bootstrap_identity_and_scope") as mock_scope:
                with patch("agentic_devtools.cli.workflows.commands.initiate_workflow"):
                    with patch("agentic_devtools.cli.workflows.commands._copy_review_state_to_apply_suggestions"):
                        with patch(
                            "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_apply_pr_suggestions"
                        ):
                            commands.initiate_apply_pull_request_review_suggestions_workflow(
                                _argv=["--pull-request-id", "25858"]
                            )

        mock_scope.assert_called_once_with("PR25858")


class TestInitiateApplyPRSuggestionsStaleKeyCleanup:
    """Tests that stale context keys from a prior run are cleaned up appropriately.

    clear_state_for_workflow_initiation() only removes workflow tracking keys
    (workflow, agdt_run_id) and preserves context keys like jira.issue_key and
    pull_request_id.  Without explicit cleanup, a stale key from a prior run can
    silently bleed into the new session.
    """

    def test_stale_issue_key_cleared_when_only_pr_id_provided(self, temp_state_dir, clear_state_before):
        """When only --pull-request-id is given, a stale jira.issue_key must be deleted.

        Without this cleanup the derive-from-PR path (which attempts to extract
        an issue key from the PR source branch) is never reached, because
        resolved_issue_key is truthy from the stale value.
        """
        # Simulate stale state left over from a prior run
        state.set_value("jira.issue_key", "STALE-999")

        with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
            with patch("agentic_devtools.cli.workflows.commands._ensure_bootstrap_identity_and_scope"):
                with patch("agentic_devtools.cli.workflows.commands.initiate_workflow"):
                    with patch("agentic_devtools.cli.workflows.commands._copy_review_state_to_apply_suggestions"):
                        with patch(
                            "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_apply_pr_suggestions"
                        ):
                            commands.initiate_apply_pull_request_review_suggestions_workflow(
                                _argv=["--pull-request-id", "123"]
                            )

        # The stale issue key must have been deleted, not silently reused
        assert state.get_value("jira.issue_key") is None

    def test_stale_pr_id_cleared_when_only_issue_key_provided(self, temp_state_dir, clear_state_before):
        """When only --issue-key is given, a stale pull_request_id must be deleted."""
        # Simulate stale state left over from a prior run
        state.set_value("pull_request_id", "STALE-42")

        with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
            with patch("agentic_devtools.cli.workflows.commands._ensure_bootstrap_identity_and_scope"):
                with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
                    from agentic_devtools.cli.workflows.preflight import PreflightResult

                    mock_pf.return_value = PreflightResult(
                        folder_valid=True,
                        branch_valid=True,
                        folder_name="DFLY-1234",
                        branch_name="feature/DFLY-1234/impl",
                        issue_key="DFLY-1234",
                    )
                    with patch("agentic_devtools.cli.workflows.commands.initiate_workflow"):
                        with patch("agentic_devtools.cli.workflows.commands._copy_review_state_to_apply_suggestions"):
                            with patch(
                                "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_apply_pr_suggestions"
                            ):
                                commands.initiate_apply_pull_request_review_suggestions_workflow(
                                    _argv=["--issue-key", "DFLY-1234"]
                                )

        # The stale PR ID must have been deleted, not silently reused
        assert state.get_value("pull_request_id") is None
