"""Tests for TestInitiateApplyPRSuggestionsWorkflowBranches."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import commands
from agentic_devtools.prompts import loader


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


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


class TestInitiateApplyPRSuggestionsWorkflowBranches:
    """Test additional branches in initiate_apply_pull_request_review_suggestions_workflow."""

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
        assert "continue the workflow in the new VS Code window" in captured.out

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

            # Execute command
            commands.initiate_apply_pull_request_review_suggestions_workflow(_argv=[])

        # Verify
        workflow = state.get_workflow_state()
        assert workflow["active"] == "apply-pull-request-review-suggestions"
