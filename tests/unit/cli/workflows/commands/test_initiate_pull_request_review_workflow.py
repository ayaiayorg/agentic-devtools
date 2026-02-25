"""Tests for TestInitiatePRReviewWorkflowBranches."""

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
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


@pytest.fixture
def mock_workflow_state_clearing():
    """Mock clear_state_for_workflow_initiation to be a no-op.

    This is needed because workflow initiation commands clear all state at the start,
    but tests set up state before calling the command. Without this mock, the test's
    state setup would be wiped immediately.
    """
    with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
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

            with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
                mock_src.return_value = "feature/DFLY-1234/test"

                with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                    mock_setup.return_value = True
                    commands.initiate_pull_request_review_workflow(_argv=[])

        captured = capsys.readouterr()
        assert "Not in the correct context" in captured.out
        assert "continue the workflow in the new VS Code window" in captured.out

    def test_pr_review_preflight_fails_with_auto_setup_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test PR review when preflight fails and auto_setup also fails."""
        state.set_value("pull_request_id", "123")
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

            with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
                mock_src.return_value = "feature/DFLY-1234/test"

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


class TestWorkflowCommands:
    """Tests for individual workflow command functions."""

    def test_pull_request_review_workflow(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test pull request review workflow command starts background task."""
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

                    # Mock background task to avoid actual async operations
                    with patch(
                        "agentic_devtools.cli.azure_devops.async_commands.get_pull_request_details_async"
                    ) as mock_async:
                        mock_async.return_value = None

                        # Execute command
                        commands.initiate_pull_request_review_workflow(_argv=[])

        # Verify: The new implementation starts a background task instead of
        # immediately rendering the prompt. Workflow state is set by the background
        # task (get_pull_request_details) after it completes.
        captured = capsys.readouterr()
        assert "Initiating pull request review for PR #123" in captured.out
        assert "Background task started" in captured.out
        assert "agdt-task-wait" in captured.out

        task_id = state.get_value("background.task_id")
        assert task_id is not None

    def test_pull_request_review_workflow_with_issue_key_from_jira(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test PR review workflow finds PR from Jira issue via unified helper."""
        # Mock the unified helper to return a PR ID (it internally checks Jira first)
        with patch("agentic_devtools.cli.azure_devops.helpers.find_pr_from_jira_issue") as mock_find_pr:
            mock_find_pr.return_value = 456

            # Mock get_pull_request_source_branch to return the PR's source branch
            with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_get_branch:
                mock_get_branch.return_value = "feature/DFLY-1234/implementation"

                # Mock preflight to pass (patch at the commands module level where it's imported)
                with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
                    from agentic_devtools.cli.workflows.preflight import PreflightResult

                    mock_preflight.return_value = PreflightResult(
                        folder_valid=True,
                        branch_valid=True,
                        folder_name="DFLY-1234",
                        branch_name="feature/DFLY-1234/implementation",
                        issue_key="DFLY-1234",
                    )

                    # Also mock perform_auto_setup to prevent actual worktree creation in case it's called
                    with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_auto_setup:
                        mock_auto_setup.return_value = True

                        # Mock background task to avoid actual async operations
                        with patch(
                            "agentic_devtools.cli.azure_devops.async_commands.get_pull_request_details_async"
                        ) as mock_async:
                            mock_async.return_value = None

                            # Execute command with issue key
                            commands.initiate_pull_request_review_workflow(_argv=["--issue-key", "DFLY-1234"])

        # Verify it found the PR and started the workflow
        captured = capsys.readouterr()
        assert "Found PR #456" in captured.out
        assert "Initiating pull request review for PR #456" in captured.out

        # Verify state was updated (pull_request_id is stored as int by setup_pull_request_review_async)
        assert state.get_value("pull_request_id") == 456
        assert state.get_value("jira.issue_key") == "DFLY-1234"

    def test_pull_request_review_workflow_with_issue_key_fallback_to_azure_devops(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test PR review workflow falls back to Azure DevOps search when Jira has no link."""
        # Mock the unified helper - it internally tries Jira first, then ADO
        # Here we simulate it finding the PR from ADO (via the unified helper)
        with patch("agentic_devtools.cli.azure_devops.helpers.find_pr_from_jira_issue") as mock_find_pr:
            mock_find_pr.return_value = 789

            # Mock get_pull_request_source_branch to return the PR's source branch
            with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_get_branch:
                mock_get_branch.return_value = "feature/DFLY-1234/implementation"

                # Mock preflight to pass (we're in correct context)
                with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
                    from agentic_devtools.cli.workflows.preflight import PreflightResult

                    mock_preflight.return_value = PreflightResult(
                        folder_valid=True,
                        branch_valid=True,
                        folder_name="DFLY-1234",
                        branch_name="feature/DFLY-1234/implementation",
                        issue_key="DFLY-1234",
                    )

                    # Also mock perform_auto_setup to prevent actual worktree creation in case it's called
                    with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_auto_setup:
                        mock_auto_setup.return_value = True

                        # Mock background task to avoid actual async operations
                        with patch(
                            "agentic_devtools.cli.azure_devops.async_commands.get_pull_request_details_async"
                        ) as mock_async:
                            mock_async.return_value = None

                            commands.initiate_pull_request_review_workflow(_argv=["--issue-key", "DFLY-1234"])

        captured = capsys.readouterr()
        # The unified helper now abstracts the Jira vs ADO fallback logic
        assert "Found PR #789" in captured.out
        assert state.get_value("pull_request_id") == 789

    def test_pull_request_review_workflow_with_issue_key_not_found(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test PR review workflow exits when no PR found for issue key."""
        # Mock unified helper to return None (no PR found anywhere)
        with patch("agentic_devtools.cli.azure_devops.helpers.find_pr_from_jira_issue") as mock_find_pr:
            mock_find_pr.return_value = None

            with pytest.raises(SystemExit) as exc_info:
                commands.initiate_pull_request_review_workflow(_argv=["--issue-key", "DFLY-9999"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No active PR found for issue key 'DFLY-9999'" in captured.out

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
        state.set_value("jira.issue_key", "DFLY-1234")

        with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
            mock_src.return_value = "feature/DFLY-1234/test"

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
                    commands.initiate_pull_request_review_workflow(_argv=["--interactive", "false"])

        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["interactive"] is False

    def test_interactive_defaults_to_true(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that interactive defaults to True when not specified."""
        state.set_value("pull_request_id", "456")
        state.set_value("jira.issue_key", "DFLY-5678")

        with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
            mock_src.return_value = "feature/DFLY-5678/test"

            with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
                from agentic_devtools.cli.workflows.preflight import PreflightResult

                mock_preflight.return_value = PreflightResult(
                    folder_valid=False,
                    branch_valid=False,
                    folder_name="wrong",
                    branch_name="main",
                    issue_key="DFLY-5678",
                )

                with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                    mock_setup.return_value = True
                    commands.initiate_pull_request_review_workflow(_argv=[])

        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["interactive"] is True

    def test_auto_execute_command_passed_with_pr_id_and_issue_key(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that auto_execute_command includes both PR ID and issue key when both are available."""
        state.set_value("pull_request_id", "789")
        state.set_value("jira.issue_key", "DFLY-9999")

        with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch") as mock_src:
            mock_src.return_value = "feature/DFLY-9999/impl"

            with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
                from agentic_devtools.cli.workflows.preflight import PreflightResult

                mock_preflight.return_value = PreflightResult(
                    folder_valid=False,
                    branch_valid=False,
                    folder_name="wrong",
                    branch_name="main",
                    issue_key="DFLY-9999",
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
            "DFLY-9999",
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
