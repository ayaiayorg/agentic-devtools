"""Tests for TestInitiatePRReviewWorkflowBranches."""

import json
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


class TestInitiatePRReviewWorkflowBranches:
    """Test additional branches in initiate_pull_request_review_workflow."""

    def test_missing_both_pr_id_and_issue_key(self, temp_state_dir, clear_state_before, capsys):
        """Test error when neither --pull-request-id nor --issue-key is provided."""
        with pytest.raises(SystemExit) as exc_info:
            commands.initiate_pull_request_review_workflow(_argv=[])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Either --pull-request-id or --issue-key must be provided" in captured.out

    def test_pr_review_preflight_fails_with_auto_setup_returns(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test PR review when preflight fails and auto_setup succeeds (returns early)."""
        state.set_value("pull_request_id", "123")
        state.set_value("jira.issue_key", "PROJECT-1234")

        with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1234",
            )

            with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
                mock_src.return_value = "feature/PROJECT-1234/test"

                with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                    mock_setup.return_value = True
                    commands.initiate_pull_request_review_workflow(_argv=[])

        captured = capsys.readouterr()
        assert "Not in the correct context" in captured.out
        assert "Copilot session will start automatically" in captured.out

    def test_pr_review_preflight_fails_with_auto_setup_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test PR review when preflight fails and auto_setup also fails."""
        state.set_value("pull_request_id", "123")
        state.set_value("jira.issue_key", "PROJECT-1234")

        with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1234",
            )

            with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
                mock_src.return_value = "feature/PROJECT-1234/test"

                with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                    mock_setup.return_value = False
                    with pytest.raises(SystemExit) as exc_info:
                        commands.initiate_pull_request_review_workflow(_argv=[])
                    assert exc_info.value.code == 1

    def test_pr_review_source_branch_fetch_exception(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test PR review exits with error when source branch fetch fails.

        Since source branch is required to checkout the correct code for review,
        failing to get it should result in a clear error.
        """
        state.set_value("pull_request_id", "123")

        # Mock find_jira_issue_from_pr (called first when we have PR but no issue key)
        # and get_pull_request_source_branch (which should raise an exception)
        with patch("agentic_devtools.cli.azure_devops.helpers.find_jira_issue_from_pr") as mock_find:
            mock_find.return_value = None  # No issue found

            with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
                mock_src.side_effect = Exception("API error")

                with pytest.raises(SystemExit) as exc_info:
                    commands.initiate_pull_request_review_workflow(_argv=[])
                assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Could not fetch PR source branch" in captured.err
        assert "Unable to determine source branch" in captured.err

    def test_stale_issue_key_cleared_when_not_provided(self, temp_state_dir, clear_state_before):
        """Test that a stale jira.issue_key from a prior run is NOT reused.

        When --pull-request-id is provided without --issue-key, any jira.issue_key
        left in state from a previous run must be cleared before the cross-lookup,
        so an unrelated Jira issue cannot contaminate the new review session.
        """
        # Simulate stale state left over from a prior run
        state.set_value("jira.issue_key", "STALE-999")

        with patch("agentic_devtools.cli.azure_devops.helpers.find_jira_issue_from_pr") as mock_find:
            mock_find.return_value = None  # cross-lookup finds nothing

            with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
                mock_src.side_effect = Exception("stop early")

                with pytest.raises(SystemExit):
                    commands.initiate_pull_request_review_workflow(_argv=["--pull-request-id", "123"])

        # The stale issue key must have been deleted, not silently reused
        assert state.get_value("jira.issue_key") is None
        # The PR→issue cross-lookup must have been called (proving resolved_issue_key was None)
        mock_find.assert_called_once_with(123)

    def test_stale_pull_request_id_cleared_when_not_provided(self, temp_state_dir, clear_state_before):
        """Test that a stale pull_request_id from a prior run is NOT reused.

        When --issue-key is provided without --pull-request-id, any pull_request_id
        left in state from a previous run must be cleared before the cross-lookup,
        so an unrelated PR cannot contaminate the new review session.
        """
        # Simulate stale state left over from a prior run
        state.set_value("pull_request_id", "STALE-42")

        with patch("agentic_devtools.cli.azure_devops.helpers.find_pr_from_jira_issue") as mock_find_pr:
            mock_find_pr.return_value = None  # cross-lookup finds nothing

            with pytest.raises(SystemExit):
                commands.initiate_pull_request_review_workflow(_argv=["--issue-key", "PROJECT-1234"])

        # The stale PR ID must have been deleted, not silently reused
        assert state.get_value("pull_request_id") is None
        # The issue→PR cross-lookup must have been called (proving resolved_pr_id was None)
        mock_find_pr.assert_called_once_with("PROJECT-1234", verbose=True)

    def test_pr_review_with_both_args_uses_cli_values_not_state(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Regression: both --pull-request-id and --issue-key avoid the 'missing args' error.

        Validates the core fix: resolved_pr_id/resolved_issue_key are derived from the
        already-parsed CLI local variables (not via a get_value() state round-trip), so
        the function proceeds correctly even if the state directory changes after set_value()
        or bootstrap-related behavior differs.
        """
        from agentic_devtools.cli.workflows.preflight import PreflightResult

        with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
            mock_src.return_value = "feature/PROJECT-2779/implementation"

            with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
                mock_preflight.return_value = PreflightResult(
                    folder_valid=True,
                    branch_valid=True,
                    folder_name="PROJECT-2779",
                    branch_name="feature/PROJECT-2779/implementation",
                    issue_key="PROJECT-2779",
                )

                with patch(
                    "agentic_devtools.cli.workflows.commands.get_git_repo_root",
                    return_value="/fake/repo-root",
                ):
                    with patch("agentic_devtools.cli.azure_devops.async_commands.setup_pull_request_review_async"):
                        with patch(
                            "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_pr_review"
                        ):
                            # Should NOT raise SystemExit with "Either --pull-request-id or
                            # --issue-key must be provided" — the fix ensures CLI local vars
                            # are used directly rather than relying on a state round-trip.
                            commands.initiate_pull_request_review_workflow(
                                _argv=["--pull-request-id", "25858", "--issue-key", "PROJECT-2779"]
                            )

        captured = capsys.readouterr()
        assert "Either --pull-request-id or --issue-key must be provided" not in captured.out

    def test_pr_review_with_only_pr_id_and_missing_bootstrap(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Only --pull-request-id triggers cross-lookup (not a missing-args error).

        Validates that resolved_pr_id is derived from the CLI local variable so the
        PR→Jira cross-lookup branch is entered when only --pull-request-id is given,
        rather than erroring with "Either --pull-request-id or --issue-key must be
        provided" due to a state-directory shift.
        """
        with patch("agentic_devtools.cli.azure_devops.helpers.find_jira_issue_from_pr") as mock_find:
            mock_find.return_value = None  # cross-lookup finds nothing

            with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
                mock_src.side_effect = Exception("stop early")

                # Should reach the cross-lookup (and then fail on source branch), NOT the
                # "Either --pull-request-id or --issue-key must be provided" error.
                with pytest.raises(SystemExit) as exc_info:
                    commands.initiate_pull_request_review_workflow(_argv=["--pull-request-id", "25858"])
                assert exc_info.value.code == 1

        captured = capsys.readouterr()
        # Cross-lookup was attempted, so no "Either ... must be provided" message
        assert "Either --pull-request-id or --issue-key must be provided" not in captured.out
        # The PR→Jira cross-lookup must have been called
        mock_find.assert_called_once_with(25858)


@pytest.fixture
def mock_copilot_session():
    """Mock Copilot session + background setup to prevent real subprocesses in tests."""
    with patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_pr_review") as mock:
        with patch("agentic_devtools.cli.azure_devops.async_commands.setup_pull_request_review_async"):
            yield mock


class TestWorkflowCommands:
    """Tests for individual workflow command functions."""

    def test_pull_request_review_workflow(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        mock_copilot_session,
        capsys,
    ):
        """Test pull request review workflow command initiates PR review."""
        # Setup state
        state.set_value("pull_request_id", "123")

        # Mock get_pull_request_source_branch to return the PR's source branch
        with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_get_branch:
            mock_get_branch.return_value = "feature/some-branch"

            # Mock the cross-lookup helper that's called when we have PR but no issue key
            with patch("agentic_devtools.cli.azure_devops.helpers.find_jira_issue_from_pr") as mock_find:
                mock_find.return_value = None  # No issue found

                # Mock preflight to pass - when no Jira issue, uses PR{id} as worktree identifier
                with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
                    from agentic_devtools.cli.workflows.preflight import PreflightResult

                    mock_preflight.return_value = PreflightResult(
                        folder_valid=True,
                        branch_valid=True,
                        folder_name="PR123",
                        branch_name="feature/some-branch",
                        issue_key=None,
                    )

                    # Execute command (setup_pull_request_review_async is mocked by fixture)
                    commands.initiate_pull_request_review_workflow(_argv=[])

        captured = capsys.readouterr()
        assert "Initiating pull request review for PR #123" in captured.out

    def test_pull_request_review_workflow_with_issue_key_from_jira(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, mock_copilot_session, capsys
    ):
        """Test PR review workflow finds PR from Jira issue via unified helper."""
        # Mock the unified helper to return a PR ID (it internally checks Jira first)
        with patch("agentic_devtools.cli.azure_devops.helpers.find_pr_from_jira_issue") as mock_find_pr:
            mock_find_pr.return_value = 456

            # Mock get_pull_request_source_branch to return the PR's source branch
            with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_get_branch:
                mock_get_branch.return_value = "feature/PROJECT-1234/implementation"

                # Mock preflight to pass (patch at the commands module level where it's imported)
                with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
                    from agentic_devtools.cli.workflows.preflight import PreflightResult

                    mock_preflight.return_value = PreflightResult(
                        folder_valid=True,
                        branch_valid=True,
                        folder_name="PROJECT-1234",
                        branch_name="feature/PROJECT-1234/implementation",
                        issue_key="PROJECT-1234",
                    )

                    # Also mock perform_auto_setup to prevent actual worktree creation in case it's called
                    with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_auto_setup:
                        mock_auto_setup.return_value = True

                        # Execute command with issue key (setup_pull_request_review_async is mocked by fixture)
                        commands.initiate_pull_request_review_workflow(_argv=["--issue-key", "PROJECT-1234"])

        # Verify it found the PR and started the workflow
        captured = capsys.readouterr()
        assert "Found PR #456" in captured.out
        assert "Initiating pull request review for PR #456" in captured.out

        # Verify state was updated (stored as string by commands.py; setup_pull_request_review_async is mocked)
        assert str(state.get_value("pull_request_id")) == "456"
        assert state.get_value("jira.issue_key") == "PROJECT-1234"

    def test_pull_request_review_workflow_with_issue_key_fallback_to_azure_devops(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, mock_copilot_session, capsys
    ):
        """Test PR review workflow falls back to Azure DevOps search when Jira has no link."""
        # Mock the unified helper - it internally tries Jira first, then ADO
        # Here we simulate it finding the PR from ADO (via the unified helper)
        with patch("agentic_devtools.cli.azure_devops.helpers.find_pr_from_jira_issue") as mock_find_pr:
            mock_find_pr.return_value = 789

            # Mock get_pull_request_source_branch to return the PR's source branch
            with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_get_branch:
                mock_get_branch.return_value = "feature/PROJECT-1234/implementation"

                # Mock preflight to pass (we're in correct context)
                with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
                    from agentic_devtools.cli.workflows.preflight import PreflightResult

                    mock_preflight.return_value = PreflightResult(
                        folder_valid=True,
                        branch_valid=True,
                        folder_name="PROJECT-1234",
                        branch_name="feature/PROJECT-1234/implementation",
                        issue_key="PROJECT-1234",
                    )

                    # Also mock perform_auto_setup to prevent actual worktree creation in case it's called
                    with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_auto_setup:
                        mock_auto_setup.return_value = True

                        # Execute (setup_pull_request_review_async is mocked by fixture)
                        commands.initiate_pull_request_review_workflow(_argv=["--issue-key", "PROJECT-1234"])

        captured = capsys.readouterr()
        # The unified helper now abstracts the Jira vs ADO fallback logic
        assert "Found PR #789" in captured.out
        assert str(state.get_value("pull_request_id")) == "789"

    def test_pull_request_review_workflow_with_issue_key_not_found(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test PR review workflow exits when no PR found for issue key."""
        # Mock unified helper to return None (no PR found anywhere)
        with patch("agentic_devtools.cli.azure_devops.helpers.find_pr_from_jira_issue") as mock_find_pr:
            mock_find_pr.return_value = None

            with pytest.raises(SystemExit) as exc_info:
                commands.initiate_pull_request_review_workflow(_argv=["--issue-key", "PROJECT-9999"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No active PR found for issue key 'PROJECT-9999'" in captured.out

    def test_pull_request_review_workflow_source_branch_not_found(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test PR review workflow exits when source branch cannot be fetched."""
        # Mock get_pull_request_source_branch to return None (branch fetch failed)
        with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_get_branch:
            mock_get_branch.return_value = None

            # Mock the cross-lookup helper
            with patch("agentic_devtools.cli.azure_devops.helpers.find_jira_issue_from_pr") as mock_find:
                mock_find.return_value = None

                with pytest.raises(SystemExit) as exc_info:
                    # Pass PR ID via command line since state gets cleared at start
                    commands.initiate_pull_request_review_workflow(_argv=["--pull-request-id", "999"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Unable to determine source branch for PR #999" in captured.err


class TestInitiatePRReviewWorkflowInteractive:
    """Tests for the --interactive flag and auto_execute_command behaviour."""

    def test_interactive_flag_false_parsed_from_cli(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that --interactive false disables interactive mode."""
        state.set_value("pull_request_id", "123")
        state.set_value("jira.issue_key", "PROJECT-1234")

        with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
            mock_src.return_value = "feature/PROJECT-1234/test"

            with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
                from agentic_devtools.cli.workflows.preflight import PreflightResult

                mock_preflight.return_value = PreflightResult(
                    folder_valid=False,
                    branch_valid=False,
                    folder_name="wrong",
                    branch_name="main",
                    issue_key="PROJECT-1234",
                )

                with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                    mock_setup.return_value = True
                    commands.initiate_pull_request_review_workflow(_argv=["--interactive", "false"])

        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["interactive"] is False

    def test_interactive_defaults_to_false(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that interactive defaults to False when not specified."""
        state.set_value("pull_request_id", "456")
        state.set_value("jira.issue_key", "PROJECT-5678")

        with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
            mock_src.return_value = "feature/PROJECT-5678/test"

            with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
                from agentic_devtools.cli.workflows.preflight import PreflightResult

                mock_preflight.return_value = PreflightResult(
                    folder_valid=False,
                    branch_valid=False,
                    folder_name="wrong",
                    branch_name="main",
                    issue_key="PROJECT-5678",
                )

                with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                    mock_setup.return_value = True
                    commands.initiate_pull_request_review_workflow(_argv=[])

        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["interactive"] is False

    def test_auto_execute_command_passed_with_pr_id_and_issue_key(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that auto_execute_command includes both PR ID and issue key when both are available."""
        state.set_value("pull_request_id", "789")
        state.set_value("jira.issue_key", "PROJECT-9999")

        with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
            mock_src.return_value = "feature/PROJECT-9999/impl"

            with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
                from agentic_devtools.cli.workflows.preflight import PreflightResult

                mock_preflight.return_value = PreflightResult(
                    folder_valid=False,
                    branch_valid=False,
                    folder_name="wrong",
                    branch_name="main",
                    issue_key="PROJECT-9999",
                )

                with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                    mock_setup.return_value = True
                    commands.initiate_pull_request_review_workflow(_argv=[])

        call_kwargs = mock_setup.call_args[1]
        expected_cmd = [
            "agdt-initiate-pull-request-review-workflow",
            "--pull-request-id",
            "789",
            "--issue-key",
            "PROJECT-9999",
            "--interactive",
            "false",
        ]
        assert call_kwargs["auto_execute_command"] == expected_cmd

    def test_auto_execute_command_without_issue_key(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that auto_execute_command omits --issue-key when no issue key is available."""
        state.set_value("pull_request_id", "111")

        with patch("agentic_devtools.cli.azure_devops.helpers.find_jira_issue_from_pr") as mock_find:
            mock_find.return_value = None  # No issue key

            with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
                mock_src.return_value = "feature/some-branch"

                with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
                    from agentic_devtools.cli.workflows.preflight import PreflightResult

                    mock_preflight.return_value = PreflightResult(
                        folder_valid=False,
                        branch_valid=False,
                        folder_name="wrong",
                        branch_name="main",
                        issue_key="PR111",
                    )

                    with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                        mock_setup.return_value = True
                        commands.initiate_pull_request_review_workflow(_argv=[])

        call_kwargs = mock_setup.call_args[1]
        auto_cmd = call_kwargs["auto_execute_command"]
        assert "--pull-request-id" in auto_cmd
        assert "111" in auto_cmd
        assert "--issue-key" not in auto_cmd
        assert "--interactive" in auto_cmd
        assert "false" in auto_cmd

    def test_auto_execute_command_includes_interactive_true(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that auto_execute_command includes --interactive true when interactive is explicitly set."""
        state.set_value("pull_request_id", "789")
        state.set_value("jira.issue_key", "PROJECT-9999")

        with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
            mock_src.return_value = "feature/PROJECT-9999/impl"

            with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
                from agentic_devtools.cli.workflows.preflight import PreflightResult

                mock_preflight.return_value = PreflightResult(
                    folder_valid=False,
                    branch_valid=False,
                    folder_name="wrong",
                    branch_name="main",
                    issue_key="PROJECT-9999",
                )

                with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                    mock_setup.return_value = True
                    commands.initiate_pull_request_review_workflow(_argv=["--interactive", "true"])

        call_kwargs = mock_setup.call_args[1]
        auto_cmd = call_kwargs["auto_execute_command"]
        assert "--interactive" in auto_cmd
        interactive_idx = auto_cmd.index("--interactive")
        assert auto_cmd[interactive_idx + 1] == "true"


class TestInitiatePRReviewWorkflowCopilotSession:
    """Tests for the Copilot session started after preflight passes."""

    def _run_with_preflight_passing(self, pr_id, source_branch, issue_key=None, argv=None):
        """Helper: run initiate_pull_request_review_workflow with preflight passing."""
        from agentic_devtools.cli.workflows.preflight import PreflightResult

        argv = argv or []
        state.set_value("pull_request_id", pr_id)
        if issue_key:
            state.set_value("jira.issue_key", issue_key)

        with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
            mock_src.return_value = source_branch
            with patch("agentic_devtools.cli.azure_devops.helpers.find_jira_issue_from_pr") as mock_find:
                mock_find.return_value = None
                with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
                    mock_preflight.return_value = PreflightResult(
                        folder_valid=True,
                        branch_valid=True,
                        folder_name="PR999",
                        branch_name=source_branch,
                        issue_key=issue_key,
                    )
                    with patch(
                        "agentic_devtools.cli.workflows.commands.get_git_repo_root",
                        return_value="/fake/repo-root",
                    ):
                        with patch("agentic_devtools.cli.azure_devops.async_commands.setup_pull_request_review_async"):
                            with patch(
                                "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_pr_review"
                            ) as mock_session:
                                commands.initiate_pull_request_review_workflow(_argv=argv)
                                return mock_session

    def test_copilot_session_started_when_preflight_passes(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing
    ):
        """_start_copilot_session_for_pr_review is called with the repo root (not cwd)."""
        mock_session = self._run_with_preflight_passing("999", "feature/some-branch")
        mock_session.assert_called_once()
        call_kwargs = mock_session.call_args
        assert call_kwargs[0][0] == "/fake/repo-root"

    def test_copilot_session_interactive_default_is_false(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing
    ):
        """_start_copilot_session_for_pr_review is called with interactive=False by default."""
        mock_session = self._run_with_preflight_passing("999", "feature/some-branch")
        mock_session.assert_called_once_with("/fake/repo-root", interactive=False)

    def test_copilot_session_respects_interactive_false(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing
    ):
        """_start_copilot_session_for_pr_review is called with interactive=False when --interactive false."""
        mock_session = self._run_with_preflight_passing("999", "feature/some-branch", argv=["--interactive", "false"])
        mock_session.assert_called_once_with("/fake/repo-root", interactive=False)

    def test_copilot_session_interactive_true_when_explicitly_set(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing
    ):
        """_start_copilot_session_for_pr_review is called with interactive=True when --interactive true."""
        mock_session = self._run_with_preflight_passing("999", "feature/some-branch", argv=["--interactive", "true"])
        mock_session.assert_called_once_with("/fake/repo-root", interactive=True)


class TestInitiatePRReviewWorkflowBootstrapScope:
    """Tests that the correct worktree_key scope is set before any set_value() calls."""

    def test_both_pr_id_and_issue_key_uses_issue_key_as_worktree_key(self, temp_state_dir, clear_state_before):
        """When both --pull-request-id and --issue-key are provided, worktree_key is the issue key.

        Issue key takes priority over PR ID so that all state is written to a single
        scoped directory (e.g., PROJECT-2779/) rather than being scattered across multiple
        directories.  _ensure_bootstrap_identity_and_scope must be called with the issue
        key BEFORE any set_value() calls.
        """
        with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
            with patch("agentic_devtools.cli.workflows.commands._ensure_bootstrap_identity_and_scope") as mock_scope:
                with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
                    mock_src.side_effect = Exception("stop after scope call")

                    with pytest.raises(SystemExit):
                        commands.initiate_pull_request_review_workflow(
                            _argv=["--pull-request-id", "25858", "--issue-key", "PROJECT-2779"]
                        )

        mock_scope.assert_called_once_with("PROJECT-2779")

    def test_only_pr_id_uses_pr_worktree_key(self, temp_state_dir, clear_state_before):
        """When only --pull-request-id is provided, worktree_key is PR{id}.

        _ensure_bootstrap_identity_and_scope must be called with 'PR<id>' when no
        issue key is provided.
        """
        with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
            with patch("agentic_devtools.cli.workflows.commands._ensure_bootstrap_identity_and_scope") as mock_scope:
                with patch("agentic_devtools.cli.azure_devops.helpers.find_jira_issue_from_pr") as mock_find:
                    mock_find.return_value = None

                    with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
                        mock_src.side_effect = Exception("stop after scope call")

                        with pytest.raises(SystemExit):
                            commands.initiate_pull_request_review_workflow(_argv=["--pull-request-id", "25858"])

        mock_scope.assert_called_once_with("PR25858")

    def test_only_issue_key_uses_issue_key_as_worktree_key(self, temp_state_dir, clear_state_before):
        """When only --issue-key is provided, worktree_key is the issue key."""
        with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
            with patch("agentic_devtools.cli.workflows.commands._ensure_bootstrap_identity_and_scope") as mock_scope:
                with patch("agentic_devtools.cli.azure_devops.helpers.find_pr_from_jira_issue") as mock_find_pr:
                    mock_find_pr.return_value = None  # no PR found → sys.exit(1)

                    with pytest.raises(SystemExit):
                        commands.initiate_pull_request_review_workflow(_argv=["--issue-key", "PROJECT-2779"])

        mock_scope.assert_called_once_with("PROJECT-2779")


class TestInitiatePRReviewWorkflowWorktreeKeyNormalization:
    """Tests that issue_key and pull_request_id are stripped before building worktree_key.

    Leading/trailing whitespace in either value would cause is_safe_dir_segment() to
    reject the segment and fall back to _unscoped, reintroducing state scattering.
    """

    def test_whitespace_padded_issue_key_is_stripped(self, temp_state_dir, clear_state_before):
        """A whitespace-padded issue key is normalized before _ensure_bootstrap_identity_and_scope."""
        with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
            with patch("agentic_devtools.cli.workflows.commands._ensure_bootstrap_identity_and_scope") as mock_scope:
                with patch("agentic_devtools.cli.azure_devops.helpers.find_pr_from_jira_issue") as mock_find_pr:
                    mock_find_pr.return_value = None  # no PR found → sys.exit(1)

                    with pytest.raises(SystemExit):
                        commands.initiate_pull_request_review_workflow(
                            issue_key="  PROJECT-2779  ",
                            _argv=[],
                        )

        mock_scope.assert_called_once_with("PROJECT-2779")

    def test_whitespace_padded_pr_id_is_stripped(self, temp_state_dir, clear_state_before):
        """A whitespace-padded pull_request_id is normalized before _ensure_bootstrap_identity_and_scope."""
        with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
            with patch("agentic_devtools.cli.workflows.commands._ensure_bootstrap_identity_and_scope") as mock_scope:
                with patch("agentic_devtools.cli.azure_devops.helpers.find_jira_issue_from_pr") as mock_find:
                    mock_find.return_value = None
                    with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
                        mock_src.side_effect = Exception("stop after scope call")

                        with pytest.raises(SystemExit):
                            commands.initiate_pull_request_review_workflow(
                                pull_request_id="  25858  ",
                                _argv=[],
                            )

        mock_scope.assert_called_once_with("PR25858")


class TestMissingBootstrapStateShift:
    """Regression tests that exercise the REAL get_state_dir() to reproduce the
    state-directory shift described in the bug report.

    These tests deliberately avoid the `temp_state_dir` fixture so that
    get_state_dir() resolves paths naturally through the git-root / identity /
    bootstrap logic.  This lets set_value() trigger _update_bootstrap_worktree_key
    as a side effect and actually shift the resolved state directory mid-command.
    """

    def test_set_value_shifts_state_dir_when_bootstrap_missing(self, tmp_path, monkeypatch):
        """Prove the root cause: set_value() creates runtime-bootstrap.json, shifting get_state_dir().

        Before the fix, this shift caused a subsequent get_value() to read from the
        new scoped directory (where nothing was written) and return None.
        """
        from agentic_devtools.state import get_state_dir, get_value, set_value

        # Remove state-dir env var override so get_state_dir() uses git-root/bootstrap logic.
        monkeypatch.delenv("AGENTIC_DEVTOOLS_STATE_DIR", raising=False)

        # Create fake repo root with identity.json but NO runtime-bootstrap.json
        fake_repo = tmp_path / "fake-repo"
        fake_repo.mkdir()
        agdt_dir = fake_repo / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_text(
            json.dumps({"identity": "testuser", "email": "test@example.com"}),
            encoding="utf-8",
        )

        # _update_bootstrap_worktree_key walks up from CWD to find .agdt/
        monkeypatch.chdir(fake_repo)

        with patch("agentic_devtools.state._get_git_repo_root", return_value=fake_repo):
            # Before set_value: no bootstrap file → resolves to _unscoped
            pre_dir = get_state_dir()
            assert "_unscoped" in str(pre_dir)

            # set_value() creates runtime-bootstrap.json as a side effect
            set_value("pull_request_id", 25858)

            # The bootstrap file now exists
            bootstrap_path = agdt_dir / "runtime-bootstrap.json"
            assert bootstrap_path.exists(), "set_value() should have created runtime-bootstrap.json"

            # After set_value: identity + worktree_key present → scoped directory
            post_dir = get_state_dir()
            assert "_unscoped" not in str(post_dir)
            assert str(pre_dir) != str(post_dir), "get_state_dir() should return a different path now"

            # The state was written to pre_dir; get_value reads from post_dir → None.
            # This is the root cause of the bug: the value is unreachable after the shift.
            assert (pre_dir / "state.json").exists(), "state was written to pre_dir"
            assert not (post_dir / "state.json").exists(), "post_dir has no state.json"
            assert get_value("pull_request_id") is None, (
                "get_value() returns None after the dir shift — this is the root cause of the bug"
            )

    def test_both_args_succeed_despite_state_dir_shift(self, tmp_path, monkeypatch, capsys):
        """Both --pull-request-id and --issue-key succeed even when set_value() shifts the state dir.

        Exercises the real get_state_dir() to confirm:
        1. set_value() creates runtime-bootstrap.json (triggering the state-dir shift).
        2. The fix (using CLI local vars) prevents the misleading "argument not provided" error.
        """
        from agentic_devtools.cli.workflows.preflight import PreflightResult

        # Remove state-dir env var override so get_state_dir() uses git-root/bootstrap logic.
        monkeypatch.delenv("AGENTIC_DEVTOOLS_STATE_DIR", raising=False)

        fake_repo = tmp_path / "fake-repo"
        fake_repo.mkdir()
        agdt_dir = fake_repo / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_text(
            json.dumps({"identity": "testuser", "email": "test@example.com"}),
            encoding="utf-8",
        )

        monkeypatch.chdir(fake_repo)

        with patch("agentic_devtools.state._get_git_repo_root", return_value=fake_repo):
            with patch("agentic_devtools.cli.workflows.commands._ensure_bootstrap_identity_and_scope"):
                with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
                    mock_src.return_value = "feature/PROJECT-2779/impl"
                    with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
                        mock_preflight.return_value = PreflightResult(
                            folder_valid=True,
                            branch_valid=True,
                            folder_name="PROJECT-2779",
                            branch_name="feature/PROJECT-2779/impl",
                            issue_key="PROJECT-2779",
                        )
                        with patch(
                            "agentic_devtools.cli.workflows.commands.get_git_repo_root",
                            return_value="/fake/repo",
                        ):
                            with patch(
                                "agentic_devtools.cli.azure_devops.async_commands.setup_pull_request_review_async"
                            ):
                                with patch(
                                    "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_pr_review"
                                ):
                                    commands.initiate_pull_request_review_workflow(
                                        _argv=["--pull-request-id", "25858", "--issue-key", "PROJECT-2779"]
                                    )

        # Confirm the bootstrap file was created (state-dir shift did happen)
        assert (agdt_dir / "runtime-bootstrap.json").exists(), (
            "set_value() should have created runtime-bootstrap.json during the call"
        )
        captured = capsys.readouterr()
        assert "Either --pull-request-id or --issue-key must be provided" not in captured.out
