"""
Tests for workflow commands.
"""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import base, commands
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
    """
    Clear state before each test.

    Note: We only remove the state file, not the entire temp folder,
    to avoid deleting directories created by other fixtures (like temp_prompts_dir).
    """
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


@pytest.fixture
def mock_workflow_state_clearing():
    """
    Mock clear_state_for_workflow_initiation to be a no-op.

    This is needed because workflow initiation commands clear all state at the start,
    but tests set up state before calling the command. Without this mock, the test's
    state setup would be wiped immediately.
    """
    with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
        yield


class TestValidateRequiredState:
    """Tests for validate_required_state function."""

    def test_all_keys_present(self, temp_state_dir, clear_state_before):
        """Test validation passes when all required keys are present."""
        state.set_value("key1", "value1")
        state.set_value("key2", "value2")
        # Should not raise
        base.validate_required_state(["key1", "key2"])

    def test_missing_single_key(self, temp_state_dir, clear_state_before):
        """Test validation fails when a single key is missing."""
        state.set_value("key1", "value1")
        with pytest.raises(SystemExit) as exc_info:
            base.validate_required_state(["key1", "missing_key"])
        assert exc_info.value.code == 1

    def test_missing_multiple_keys(self, temp_state_dir, clear_state_before):
        """Test validation fails when multiple keys are missing."""
        with pytest.raises(SystemExit) as exc_info:
            base.validate_required_state(["key1", "key2"])
        assert exc_info.value.code == 1

    def test_empty_required_list(self, temp_state_dir, clear_state_before):
        """Test validation passes with empty required list."""
        # Should not raise
        base.validate_required_state([])

    def test_nested_key_present(self, temp_state_dir, clear_state_before):
        """Test validation with nested key that is present."""
        state.set_value("jira.issue_key", "DFLY-1234")
        # Should not raise
        base.validate_required_state(["jira.issue_key"])

    def test_nested_key_missing(self, temp_state_dir, clear_state_before):
        """Test validation fails with missing nested key."""
        with pytest.raises(SystemExit) as exc_info:
            base.validate_required_state(["jira.issue_key"])
        assert exc_info.value.code == 1


class TestCollectVariablesFromState:
    """Tests for collect_variables_from_state function."""

    def test_collect_simple_keys(self, temp_state_dir, clear_state_before):
        """Test collecting simple state keys."""
        state.set_value("key1", "value1")
        state.set_value("key2", "value2")
        result = base.collect_variables_from_state(["key1", "key2"])
        assert result == {"key1": "value1", "key2": "value2"}

    def test_collect_nested_keys(self, temp_state_dir, clear_state_before):
        """Test collecting nested state keys with dot notation."""
        state.set_value("jira.issue_key", "DFLY-1234")
        state.set_value("jira.project_key", "DFLY")
        result = base.collect_variables_from_state(["jira.issue_key", "jira.project_key"])
        # Keys should be converted to underscore format
        assert result["jira_issue_key"] == "DFLY-1234"
        assert result["jira_project_key"] == "DFLY"

    def test_collect_missing_optional_keys(self, temp_state_dir, clear_state_before):
        """Test that missing optional keys are skipped."""
        state.set_value("key1", "value1")
        result = base.collect_variables_from_state(["key1", "optional_missing"])
        assert result == {"key1": "value1"}

    def test_collect_empty_list(self, temp_state_dir, clear_state_before):
        """Test collecting from empty key list."""
        result = base.collect_variables_from_state([])
        assert result == {}


class TestStateKeyToVariableName:
    """Tests for _state_key_to_variable_name function."""

    def test_simple_key(self):
        """Test simple key without dots."""
        result = base._state_key_to_variable_name("simple_key")
        assert result == "simple_key"

    def test_nested_key(self):
        """Test nested key with dot notation."""
        result = base._state_key_to_variable_name("jira.issue_key")
        assert result == "jira_issue_key"

    def test_multiple_dots(self):
        """Test key with multiple dots."""
        result = base._state_key_to_variable_name("a.b.c")
        assert result == "a_b_c"


class TestInitiateWorkflow:
    """Tests for initiate_workflow function."""

    def test_initiate_workflow_success(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test successful workflow initiation."""
        # Setup template in workflow subfolder
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template = "Working on PR #{{pull_request_id}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Setup state
        state.set_value("pull_request_id", "123")

        # Initiate workflow
        base.initiate_workflow(
            workflow_name="pull-request-review",
            required_state_keys=["pull_request_id"],
            optional_state_keys=[],
        )

        # Verify workflow state
        workflow = state.get_workflow_state()
        assert workflow is not None
        assert workflow["active"] == "pull-request-review"
        assert workflow["status"] == "initiated"
        assert workflow["step"] == "initiate"

        # Verify output
        captured = capsys.readouterr()
        assert "Working on PR #123" in captured.out

    def test_initiate_workflow_missing_required_state(self, temp_state_dir, temp_prompts_dir, clear_state_before):
        """Test workflow initiation fails with missing required state."""
        # Setup template in workflow subfolder
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template = "Template {{pull_request_id}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Don't set required state
        with pytest.raises(SystemExit) as exc_info:
            base.initiate_workflow(
                workflow_name="pull-request-review",
                required_state_keys=["pull_request_id"],
                optional_state_keys=[],
            )
        assert exc_info.value.code == 1

    def test_initiate_workflow_with_optional_state(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test workflow initiation with optional state."""
        # Setup template with optional variable in workflow subfolder
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template = "PR #{{pull_request_id}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Setup required state only
        state.set_value("pull_request_id", "123")

        # Initiate workflow - should succeed even without optional state
        base.initiate_workflow(
            workflow_name="pull-request-review",
            required_state_keys=["pull_request_id"],
            optional_state_keys=["jira.issue_key"],
        )

        captured = capsys.readouterr()
        assert "PR #123" in captured.out


class TestAdvanceWorkflowStep:
    """Tests for advance_workflow_step function."""

    def test_advance_step_success(self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys):
        """Test successful step advancement."""
        # Setup initial workflow
        state.set_workflow_state(
            name="test-workflow",
            status="active",
            step="initiate",
            context={"key": "value"},
        )

        # Setup template for next step in workflow subfolder
        workflow_dir = temp_prompts_dir / "test-workflow"
        workflow_dir.mkdir()
        template = "Step 2 content"
        template_file = workflow_dir / "default-step2-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Advance step (requires workflow_name and step_name)
        base.advance_workflow_step("test-workflow", "step2")

        # Verify workflow state updated
        workflow = state.get_workflow_state()
        assert workflow["step"] == "step2"

        # Verify output
        captured = capsys.readouterr()
        assert "Step 2 content" in captured.out

    def test_advance_step_no_active_workflow(self, temp_state_dir, clear_state_before):
        """Test advancing step fails when no workflow is active."""
        with pytest.raises(SystemExit) as exc_info:
            base.advance_workflow_step("test-workflow", "step2")
        assert exc_info.value.code == 1


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

        # Verify background task was created
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
        assert "continue the workflow in the new VS Code window" in captured.out

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

                # Mock subprocess.run for the dfly-get-jira-issue call
                with patch("subprocess.run") as mock_subprocess:
                    mock_subprocess.return_value.returncode = 0

                    # Execute command
                    commands.initiate_work_on_jira_issue_workflow(_argv=[])

        # Verify - should be in planning step
        workflow = state.get_workflow_state()
        assert workflow["active"] == "work-on-jira-issue"
        assert workflow["step"] == "planning"
        captured = capsys.readouterr()
        assert "Planning work for DFLY-1234" in captured.out

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
        state.set_value("jira.project_key", "DFLY")
        state.set_value("jira.issue_key", "DFLY-1234")  # Provided issue key means continuation

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

            # Execute command with issue-key (continuation mode)
            commands.initiate_create_jira_issue_workflow(_argv=["--issue-key", "DFLY-1234"])

        # Verify
        workflow = state.get_workflow_state()
        assert workflow["active"] == "create-jira-issue"

    def test_create_jira_epic_workflow(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test create jira epic workflow command with continuation (issue key already provided)."""
        # Setup template in workflow subfolder
        workflow_dir = temp_prompts_dir / "create-jira-epic"
        workflow_dir.mkdir()
        template = "Creating epic in {{jira_project_key}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Setup state - simulate continuation after placeholder creation
        state.set_value("jira.project_key", "DFLY")
        state.set_value("jira.issue_key", "DFLY-1234")  # Provided issue key means continuation

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

            # Execute command with issue-key (continuation mode)
            commands.initiate_create_jira_epic_workflow(_argv=["--issue-key", "DFLY-1234"])

        # Verify
        workflow = state.get_workflow_state()
        assert workflow["active"] == "create-jira-epic"

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
        state.set_value("jira.parent_key", "DFLY-1234")
        state.set_value("jira.issue_key", "DFLY-1235")  # Provided issue key means continuation

        # Mock preflight to pass (we're already in correct context)
        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="DFLY-1235",
                branch_name="feature/DFLY-1234/DFLY-1235/implementation",
                issue_key="DFLY-1235",
            )

            # Execute command with issue-key (continuation mode)
            commands.initiate_create_jira_subtask_workflow(_argv=["--issue-key", "DFLY-1235"])

        # Verify
        workflow = state.get_workflow_state()
        assert workflow["active"] == "create-jira-subtask"

    def test_update_jira_issue_workflow(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test update jira issue workflow command with continuation (already in correct context)."""
        # Setup template in workflow subfolder
        workflow_dir = temp_prompts_dir / "update-jira-issue"
        workflow_dir.mkdir()
        template = "Updating issue {{jira_issue_key}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Setup state
        state.set_value("jira.issue_key", "DFLY-1234")

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

            # Execute command with issue-key
            commands.initiate_update_jira_issue_workflow(_argv=["--issue-key", "DFLY-1234"])

        # Verify
        workflow = state.get_workflow_state()
        assert workflow["active"] == "update-jira-issue"

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


class TestWorkflowCLICommands:
    """Tests for workflow CLI commands in cli/state.py."""

    def test_get_workflow_cmd_no_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test get workflow command when no workflow is active."""
        from agentic_devtools.cli.state import get_workflow_cmd

        get_workflow_cmd()
        captured = capsys.readouterr()
        assert "No workflow is currently active" in captured.out

    def test_get_workflow_cmd_with_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test get workflow command when workflow is active."""
        from agentic_devtools.cli.state import get_workflow_cmd

        state.set_workflow_state(
            name="pull-request-review",
            status="active",
            step="initiate",
            context={"pull_request_id": "123"},
        )

        get_workflow_cmd()
        captured = capsys.readouterr()
        assert "pull-request-review" in captured.out
        assert "active" in captured.out
        assert "initiate" in captured.out

    def test_clear_workflow_cmd(self, temp_state_dir, clear_state_before, capsys):
        """Test clear workflow command."""
        from agentic_devtools.cli.state import clear_workflow_cmd

        state.set_workflow_state(name="test", status="active", step="step1")
        clear_workflow_cmd()

        assert state.get_workflow_state() is None
        captured = capsys.readouterr()
        assert "Workflow 'test' cleared" in captured.out


class TestAdvanceWorkflowCmd:
    """Tests for advance_workflow_cmd entry point."""

    def test_advance_workflow_no_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test advance workflow command when no workflow is active."""
        from agentic_devtools.cli.workflows import advance_workflow_cmd

        with pytest.raises(SystemExit) as exc_info:
            advance_workflow_cmd()
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "No workflow is currently active" in captured.err

    def test_advance_workflow_unsupported_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test advance workflow command with unsupported workflow type."""
        from agentic_devtools.cli.workflows import advance_workflow_cmd

        state.set_workflow_state(name="unsupported-workflow", status="active", step="step1")

        with pytest.raises(SystemExit) as exc_info:
            advance_workflow_cmd()
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "does not support manual advancement" in captured.err

    def test_advance_workflow_work_on_jira_issue(self, temp_state_dir, clear_state_before):
        """Test advance workflow command with work-on-jira-issue workflow."""
        import sys

        from agentic_devtools.cli.workflows import advance_workflow_cmd

        state.set_workflow_state(
            name="work-on-jira-issue",
            status="active",
            step="research",
            context={"jira_issue_key": "TEST-123"},
        )

        with patch.object(sys, "argv", ["agdt-advance-workflow"]):
            with patch("agentic_devtools.cli.workflows.advance_work_on_jira_issue_workflow") as mock_advance:
                advance_workflow_cmd()
                mock_advance.assert_called_once_with(None)

    def test_advance_workflow_pull_request_review(self, temp_state_dir, clear_state_before):
        """Test advance workflow command with pull-request-review workflow."""
        import sys

        from agentic_devtools.cli.workflows import advance_workflow_cmd

        state.set_workflow_state(
            name="pull-request-review",
            status="active",
            step="review",
            context={"pull_request_id": "456"},
        )

        with patch.object(sys, "argv", ["agdt-advance-workflow"]):
            with patch("agentic_devtools.cli.workflows.advance_pull_request_review_workflow") as mock_advance:
                advance_workflow_cmd()
                mock_advance.assert_called_once_with(None)

    def test_advance_workflow_with_step_argument(self, temp_state_dir, clear_state_before):
        """Test advance workflow command with explicit step argument."""
        import sys

        from agentic_devtools.cli.workflows import advance_workflow_cmd

        state.set_workflow_state(
            name="work-on-jira-issue",
            status="active",
            step="research",
            context={"jira_issue_key": "TEST-123"},
        )

        with patch.object(sys, "argv", ["agdt-advance-workflow", "implement"]):
            with patch("agentic_devtools.cli.workflows.advance_work_on_jira_issue_workflow") as mock_advance:
                advance_workflow_cmd()
                mock_advance.assert_called_once_with("implement")


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


class TestAdvanceWorkOnJiraIssueWorkflow:
    """Tests for advance_work_on_jira_issue_workflow function."""

    def test_advance_no_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test advance fails when workflow is not active."""
        with pytest.raises(SystemExit) as exc_info:
            commands.advance_work_on_jira_issue_workflow()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "work-on-jira-issue workflow is not active" in captured.err

    def test_advance_no_workflow_state(self, temp_state_dir, clear_state_before, capsys):
        """Test advance fails when get_workflow_state returns None."""
        with patch("agentic_devtools.state.is_workflow_active", return_value=True):
            with patch("agentic_devtools.state.get_workflow_state", return_value=None):
                with pytest.raises(SystemExit) as exc_info:
                    commands.advance_work_on_jira_issue_workflow()
                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "Could not get workflow state" in captured.err

    def test_advance_auto_detects_next_step(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test advance auto-detects next step from step_order."""
        # Set up workflow in planning step
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="planning",
            context={
                "jira_issue_key": "DFLY-1234",
                "branch_name": "feature/DFLY-1234/test",
                "issue_summary": "Test issue",
            },
        )

        # Create template for checklist-creation step
        workflow_dir = temp_prompts_dir / "work-on-jira-issue"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-checklist-creation-prompt.md"
        template_file.write_text("Checklist creation for {{issue_key}}", encoding="utf-8")

        commands.advance_work_on_jira_issue_workflow()

        workflow = state.get_workflow_state()
        assert workflow["step"] == "checklist-creation"

    def test_advance_defaults_to_implementation_on_unknown_step(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test advance defaults to implementation when current step not in order."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="unknown-step",
            context={"jira_issue_key": "DFLY-1234"},
        )

        workflow_dir = temp_prompts_dir / "work-on-jira-issue"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-implementation-prompt.md"
        template_file.write_text("Implementation for {{issue_key}}", encoding="utf-8")

        commands.advance_work_on_jira_issue_workflow()

        workflow = state.get_workflow_state()
        assert workflow["step"] == "implementation"

    def test_advance_to_completion_step(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test advance to completion step sets status to completed."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="pull-request",
            context={
                "jira_issue_key": "DFLY-1234",
                "branch_name": "feature/DFLY-1234/test",
                "pull_request_url": "https://example.com/pr/123",
            },
        )
        state.set_value("pull_request_id", "123")

        workflow_dir = temp_prompts_dir / "work-on-jira-issue"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-completion-prompt.md"
        template_file.write_text("Workflow complete for {{issue_key}}", encoding="utf-8")

        commands.advance_work_on_jira_issue_workflow()

        workflow = state.get_workflow_state()
        assert workflow["step"] == "completion"
        assert workflow["status"] == "completed"


class TestAdvancePullRequestReviewWorkflow:
    """Tests for advance_pull_request_review_workflow function."""

    def test_advance_no_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test advance fails when workflow is not active."""
        with pytest.raises(SystemExit) as exc_info:
            commands.advance_pull_request_review_workflow()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "pull-request-review workflow is not active" in captured.err

    def test_advance_no_workflow_state(self, temp_state_dir, clear_state_before, capsys):
        """Test advance fails when get_workflow_state returns None."""
        with patch("agentic_devtools.state.is_workflow_active", return_value=True):
            with patch("agentic_devtools.state.get_workflow_state", return_value=None):
                with pytest.raises(SystemExit) as exc_info:
                    commands.advance_pull_request_review_workflow()
                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "Could not get workflow state" in captured.err

    def test_advance_no_pull_request_id(self, temp_state_dir, clear_state_before, capsys):
        """Test advance fails when no pull_request_id in context or state."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="initiate",
            context={},
        )

        with pytest.raises(SystemExit) as exc_info:
            commands.advance_pull_request_review_workflow()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No pull_request_id found" in captured.err

    def test_advance_invalid_pull_request_id(self, temp_state_dir, clear_state_before, capsys):
        """Test advance fails when pull_request_id is invalid."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="initiate",
            context={"pull_request_id": "not-a-number"},
        )

        with pytest.raises(SystemExit) as exc_info:
            commands.advance_pull_request_review_workflow()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid pull_request_id" in captured.err

    def test_advance_auto_detects_summary_when_all_files_complete(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test advance auto-detects summary step when all files are complete."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="file-review",
            context={"pull_request_id": "123"},
        )

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
            return_value={
                "all_complete": True,
                "completed_count": 5,
                "pending_count": 0,
                "total_count": 5,
                "current_file": None,
                "prompt_file_path": None,
            },
        ):
            workflow_dir = temp_prompts_dir / "pull-request-review"
            workflow_dir.mkdir()
            template_file = workflow_dir / "default-summary-prompt.md"
            template_file.write_text("Summary for PR #{{pull_request_id}}", encoding="utf-8")

            commands.advance_pull_request_review_workflow()

        workflow = state.get_workflow_state()
        assert workflow["step"] == "summary"

    def test_advance_stays_on_file_review_when_files_pending(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test advance stays on file-review when files are still pending."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="file-review",
            context={"pull_request_id": "123"},
        )

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
            return_value={
                "all_complete": False,
                "completed_count": 3,
                "pending_count": 2,
                "total_count": 5,
                "current_file": "src/file.py",
                "prompt_file_path": "/tmp/prompt.md",
            },
        ):
            workflow_dir = temp_prompts_dir / "pull-request-review"
            workflow_dir.mkdir()
            template_file = workflow_dir / "default-file-review-prompt.md"
            template_file.write_text("File review for PR #{{pull_request_id}}", encoding="utf-8")

            commands.advance_pull_request_review_workflow()

        workflow = state.get_workflow_state()
        assert workflow["step"] == "file-review"

    def test_advance_from_initiate_to_file_review(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test advance from initiate step goes to file-review."""
        state.set_workflow_state(
            name="pull-request-review",
            status="in-progress",
            step="initiate",
            context={"pull_request_id": "123"},
        )

        with patch(
            "agentic_devtools.cli.azure_devops.file_review_commands.get_queue_status",
            return_value={
                "all_complete": False,
                "completed_count": 0,
                "pending_count": 5,
                "total_count": 5,
                "current_file": "src/file.py",
                "prompt_file_path": "/tmp/prompt.md",
            },
        ):
            workflow_dir = temp_prompts_dir / "pull-request-review"
            workflow_dir.mkdir()
            template_file = workflow_dir / "default-file-review-prompt.md"
            template_file.write_text("File review for PR #{{pull_request_id}}", encoding="utf-8")

            commands.advance_pull_request_review_workflow()

        workflow = state.get_workflow_state()
        assert workflow["step"] == "file-review"


class TestInitiateCreateJiraIssueWorkflowBranches:
    """Test additional branches in initiate_create_jira_issue_workflow."""

    def test_preflight_fails_and_auto_setup_succeeds(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails but auto-setup succeeds (returns early)."""
        state.set_value("jira.issue_key", "DFLY-1234")
        state.set_value("jira.project_key", "DFLY")

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
                commands.initiate_create_jira_issue_workflow(_argv=["--issue-key", "DFLY-1234"])

        captured = capsys.readouterr()
        assert "Not in the correct context" in captured.out
        assert "continue the workflow in the new VS Code window" in captured.out

    def test_preflight_fails_and_auto_setup_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails and auto-setup also fails."""
        state.set_value("jira.issue_key", "DFLY-1234")
        state.set_value("jira.project_key", "DFLY")

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
                    commands.initiate_create_jira_issue_workflow(_argv=["--issue-key", "DFLY-1234"])
                assert exc_info.value.code == 1

    def test_no_issue_key_creates_placeholder(self, temp_state_dir, clear_state_before, capsys):
        """Test when no issue_key provided, calls create_placeholder_and_setup_worktree."""
        state.set_value("jira.project_key", "DFLY")

        with patch(
            "agentic_devtools.cli.workflows.worktree_setup.create_placeholder_and_setup_worktree"
        ) as mock_create:
            mock_create.return_value = (True, "DFLY-9999")
            commands.initiate_create_jira_issue_workflow(_argv=[])

        mock_create.assert_called_once()
        captured = capsys.readouterr()
        assert "continue the workflow in the new VS Code window" in captured.out

    def test_no_issue_key_placeholder_creation_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test when placeholder creation fails."""
        state.set_value("jira.project_key", "DFLY")

        with patch(
            "agentic_devtools.cli.workflows.worktree_setup.create_placeholder_and_setup_worktree"
        ) as mock_create:
            mock_create.return_value = (False, None)
            with pytest.raises(SystemExit) as exc_info:
                commands.initiate_create_jira_issue_workflow(_argv=[])
            assert exc_info.value.code == 1


class TestInitiateCreateJiraEpicWorkflowBranches:
    """Test additional branches in initiate_create_jira_epic_workflow."""

    def test_preflight_fails_and_auto_setup_succeeds(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails but auto-setup succeeds (returns early)."""
        state.set_value("jira.issue_key", "DFLY-1234")
        state.set_value("jira.project_key", "DFLY")

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
                commands.initiate_create_jira_epic_workflow(_argv=["--issue-key", "DFLY-1234"])

        captured = capsys.readouterr()
        assert "Not in the correct context" in captured.out
        assert "continue the workflow in the new VS Code window" in captured.out

    def test_preflight_fails_and_auto_setup_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails and auto-setup also fails."""
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
                    commands.initiate_create_jira_epic_workflow(_argv=["--issue-key", "DFLY-1234"])
                assert exc_info.value.code == 1

    def test_no_issue_key_creates_placeholder(self, temp_state_dir, clear_state_before, capsys):
        """Test when no issue_key provided, calls create_placeholder_and_setup_worktree."""
        state.set_value("jira.project_key", "DFLY")

        with patch(
            "agentic_devtools.cli.workflows.worktree_setup.create_placeholder_and_setup_worktree"
        ) as mock_create:
            mock_create.return_value = (True, "DFLY-9999")
            commands.initiate_create_jira_epic_workflow(_argv=[])

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["issue_type"] == "Epic"
        captured = capsys.readouterr()
        assert "continue the workflow in the new VS Code window" in captured.out

    def test_no_issue_key_placeholder_creation_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test when placeholder creation fails."""
        state.set_value("jira.project_key", "DFLY")

        with patch(
            "agentic_devtools.cli.workflows.worktree_setup.create_placeholder_and_setup_worktree"
        ) as mock_create:
            mock_create.return_value = (False, None)
            with pytest.raises(SystemExit) as exc_info:
                commands.initiate_create_jira_epic_workflow(_argv=[])
            assert exc_info.value.code == 1


class TestInitiateCreateJiraSubtaskWorkflowBranches:
    """Test additional branches in initiate_create_jira_subtask_workflow."""

    def test_preflight_fails_and_auto_setup_succeeds(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails but auto-setup succeeds (returns early)."""
        state.set_value("jira.issue_key", "DFLY-1235")
        state.set_value("jira.parent_key", "DFLY-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="DFLY-1235",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_subtask_workflow(_argv=["--issue-key", "DFLY-1235"])

        captured = capsys.readouterr()
        assert "Not in the correct context" in captured.out
        assert "continue the workflow in the new VS Code window" in captured.out

    def test_preflight_fails_and_auto_setup_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails and auto-setup also fails."""
        state.set_value("jira.issue_key", "DFLY-1235")
        state.set_value("jira.parent_key", "DFLY-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="DFLY-1235",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = False
                with pytest.raises(SystemExit) as exc_info:
                    commands.initiate_create_jira_subtask_workflow(_argv=["--issue-key", "DFLY-1235"])
                assert exc_info.value.code == 1

    def test_no_issue_key_no_parent_key_error(self, temp_state_dir, clear_state_before, capsys):
        """Test when no issue_key and no parent_key, shows error."""
        with pytest.raises(SystemExit) as exc_info:
            commands.initiate_create_jira_subtask_workflow(_argv=[])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--parent-key is required" in captured.out

    def test_no_issue_key_creates_placeholder(self, temp_state_dir, clear_state_before, capsys):
        """Test when no issue_key but parent_key provided, creates placeholder."""
        state.set_value("jira.parent_key", "DFLY-1234")

        with patch(
            "agentic_devtools.cli.workflows.worktree_setup.create_placeholder_and_setup_worktree"
        ) as mock_create:
            mock_create.return_value = (True, "DFLY-1235")
            commands.initiate_create_jira_subtask_workflow(_argv=["--parent-key", "DFLY-1234"])

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["issue_type"] == "Sub-task"
        assert call_kwargs["parent_key"] == "DFLY-1234"
        captured = capsys.readouterr()
        assert "continue the workflow in the new VS Code window" in captured.out

    def test_no_issue_key_placeholder_creation_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test when placeholder creation fails."""
        state.set_value("jira.parent_key", "DFLY-1234")

        with patch(
            "agentic_devtools.cli.workflows.worktree_setup.create_placeholder_and_setup_worktree"
        ) as mock_create:
            mock_create.return_value = (False, None)
            with pytest.raises(SystemExit) as exc_info:
                commands.initiate_create_jira_subtask_workflow(_argv=["--parent-key", "DFLY-1234"])
            assert exc_info.value.code == 1


class TestInitiateUpdateJiraIssueWorkflowBranches:
    """Test additional branches in initiate_update_jira_issue_workflow."""

    def test_missing_issue_key_error(self, temp_state_dir, clear_state_before, capsys):
        """Test error when issue_key is missing."""
        with pytest.raises(SystemExit) as exc_info:
            commands.initiate_update_jira_issue_workflow(_argv=[])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--issue-key is required" in captured.out

    def test_preflight_fails_and_auto_setup_succeeds(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails but auto-setup succeeds (returns early)."""
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
                commands.initiate_update_jira_issue_workflow(_argv=["--issue-key", "DFLY-1234"])

        captured = capsys.readouterr()
        assert "Not in the correct context" in captured.out
        assert "continue the workflow in the new VS Code window" in captured.out

    def test_preflight_fails_and_auto_setup_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails and auto-setup also fails."""
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
                    commands.initiate_update_jira_issue_workflow(_argv=["--issue-key", "DFLY-1234"])
                assert exc_info.value.code == 1


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


class TestCreateChecklistCmd:
    """Tests for create_checklist_cmd function."""

    def test_no_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test error when no workflow is active."""
        with patch("sys.argv", ["agdt-create-checklist"]):
            with pytest.raises(SystemExit) as exc_info:
                commands.create_checklist_cmd()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "requires an active work-on-jira-issue workflow" in captured.err

    def test_no_items_provided(self, temp_state_dir, clear_state_before, capsys):
        """Test error when no checklist items are provided."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="checklist-creation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        with patch("sys.argv", ["agdt-create-checklist"]):
            with pytest.raises(SystemExit) as exc_info:
                commands.create_checklist_cmd()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "No checklist items provided" in captured.err

    def test_create_checklist_success(self, temp_state_dir, clear_state_before, capsys):
        """Test successful checklist creation with items from argument."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="checklist-creation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        with patch("sys.argv", ["agdt-create-checklist", "Task 1|Task 2|Task 3"]):
            with patch("agentic_devtools.cli.workflows.manager.notify_workflow_event") as mock_event:
                from agentic_devtools.cli.workflows.manager import NotifyEventResult

                mock_event.return_value = NotifyEventResult(
                    triggered=False,
                    immediate_advance=False,
                )
                commands.create_checklist_cmd()

        captured = capsys.readouterr()
        assert "CHECKLIST CREATED" in captured.out
        assert "3 items" in captured.out

    def test_create_checklist_from_state(self, temp_state_dir, clear_state_before, capsys):
        """Test checklist creation with items from state."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="checklist-creation",
            context={"jira_issue_key": "DFLY-1234"},
        )
        state.set_value("checklist_items", "1. First task\n2. Second task")

        with patch("sys.argv", ["agdt-create-checklist"]):
            with patch("agentic_devtools.cli.workflows.manager.notify_workflow_event") as mock_event:
                from agentic_devtools.cli.workflows.manager import NotifyEventResult

                mock_event.return_value = NotifyEventResult(
                    triggered=False,
                    immediate_advance=False,
                )
                commands.create_checklist_cmd()

        captured = capsys.readouterr()
        assert "CHECKLIST CREATED" in captured.out
        assert "2 items" in captured.out

    def test_create_checklist_triggers_event(self, temp_state_dir, clear_state_before, capsys):
        """Test checklist creation triggers workflow event."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="checklist-creation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        with patch("sys.argv", ["agdt-create-checklist", "Task 1|Task 2"]):
            with patch("agentic_devtools.cli.workflows.manager.notify_workflow_event") as mock_event:
                from agentic_devtools.cli.workflows.manager import NotifyEventResult

                mock_event.return_value = NotifyEventResult(
                    triggered=True,
                    immediate_advance=False,
                )
                commands.create_checklist_cmd()

        captured = capsys.readouterr()
        assert "Workflow transition triggered" in captured.out

    def test_create_checklist_wrong_step_warning(self, temp_state_dir, clear_state_before, capsys):
        """Test warning when creating checklist in wrong step (but no existing checklist)."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",  # Not checklist-creation
            context={"jira_issue_key": "DFLY-1234"},
        )

        with patch("sys.argv", ["agdt-create-checklist", "Task 1"]):
            with patch("agentic_devtools.cli.workflows.manager.notify_workflow_event") as mock_event:
                from agentic_devtools.cli.workflows.manager import NotifyEventResult

                mock_event.return_value = NotifyEventResult(
                    triggered=False,
                    immediate_advance=False,
                )
                commands.create_checklist_cmd()

        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "not 'checklist-creation'" in captured.err


class TestUpdateChecklistCmd:
    """Tests for update_checklist_cmd function."""

    def test_no_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test error when no workflow is active."""
        with patch("sys.argv", ["agdt-update-checklist", "--complete", "1"]):
            with pytest.raises(SystemExit) as exc_info:
                commands.update_checklist_cmd()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "requires an active work-on-jira-issue workflow" in captured.err

    def test_no_existing_checklist(self, temp_state_dir, clear_state_before, capsys):
        """Test error when no checklist exists."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        with patch("sys.argv", ["agdt-update-checklist", "--complete", "1"]):
            with pytest.raises(SystemExit) as exc_info:
                commands.update_checklist_cmd()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "No checklist exists" in captured.err

    def test_no_operation_specified(self, temp_state_dir, clear_state_before, capsys):
        """Test error when no operation is specified."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        # Create a checklist first
        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1"), ChecklistItem(id=2, text="Task 2")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist"]):
            with pytest.raises(SystemExit) as exc_info:
                commands.update_checklist_cmd()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "No operation specified" in captured.err

    def test_add_item_success(self, temp_state_dir, clear_state_before, capsys):
        """Test successfully adding an item."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--add", "New task"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Added item" in captured.out
        assert "New task" in captured.out

    def test_remove_item_success(self, temp_state_dir, clear_state_before, capsys):
        """Test successfully removing an item."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--remove", "1"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Removed item 1" in captured.out

    def test_remove_item_not_found(self, temp_state_dir, clear_state_before, capsys):
        """Test removing an item that doesn't exist."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--remove", "99"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Item 99 not found" in captured.out

    def test_complete_item_success(self, temp_state_dir, clear_state_before, capsys):
        """Test marking an item as complete."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--complete", "1"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Marked item 1 complete" in captured.out

    def test_revert_item_success(self, temp_state_dir, clear_state_before, capsys):
        """Test reverting an item to incomplete."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1", completed=True)])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--revert", "1"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Reverted item 1 to incomplete" in captured.out

    def test_revert_already_incomplete(self, temp_state_dir, clear_state_before, capsys):
        """Test reverting an item that's already incomplete."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1", completed=False)])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--revert", "1"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Item 1 already incomplete" in captured.out

    def test_revert_item_not_found(self, temp_state_dir, clear_state_before, capsys):
        """Test reverting an item that doesn't exist."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--revert", "99"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Item 99 not found" in captured.out

    def test_edit_item_success(self, temp_state_dir, clear_state_before, capsys):
        """Test editing an item's text."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Old task")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--edit", "1:New task text"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Updated item 1" in captured.out

    def test_edit_item_invalid_format(self, temp_state_dir, clear_state_before, capsys):
        """Test editing with invalid format (missing colon)."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Old task")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--edit", "1-no-colon"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Invalid edit format" in captured.err

    def test_edit_item_invalid_id(self, temp_state_dir, clear_state_before, capsys):
        """Test editing with invalid item ID (not a number)."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Old task")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--edit", "abc:New text"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Invalid item ID" in captured.err

    def test_edit_item_not_found(self, temp_state_dir, clear_state_before, capsys):
        """Test editing an item that doesn't exist."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Old task")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--edit", "99:New text"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Item 99 not found" in captured.out

    def test_all_complete_triggers_event(self, temp_state_dir, clear_state_before, capsys):
        """Test completing all items triggers CHECKLIST_COMPLETE event."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--complete", "1"]):
            with patch("agentic_devtools.cli.workflows.manager.notify_workflow_event") as mock_event:
                from agentic_devtools.cli.workflows.manager import NotifyEventResult

                mock_event.return_value = NotifyEventResult(
                    triggered=True,
                    immediate_advance=False,
                )
                commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "All items complete" in captured.out
        assert "Workflow transition triggered" in captured.out


class TestShowChecklistCmd:
    """Tests for show_checklist_cmd function."""

    def test_no_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test error when no workflow is active."""
        with pytest.raises(SystemExit) as exc_info:
            commands.show_checklist_cmd()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No active work-on-jira-issue workflow" in captured.err

    def test_no_checklist_exists(self, temp_state_dir, clear_state_before, capsys):
        """Test message when no checklist exists."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        commands.show_checklist_cmd()

        captured = capsys.readouterr()
        assert "No checklist exists" in captured.out
        assert "agdt-create-checklist" in captured.out

    def test_show_checklist_with_items(self, temp_state_dir, clear_state_before, capsys):
        """Test showing a checklist with items."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(
            items=[
                ChecklistItem(id=1, text="Task 1", completed=True),
                ChecklistItem(id=2, text="Task 2"),
            ]
        )
        save_checklist(checklist)

        commands.show_checklist_cmd()

        captured = capsys.readouterr()
        assert "IMPLEMENTATION CHECKLIST (1/2 complete)" in captured.out
        assert "1 item(s) remaining" in captured.out

    def test_show_checklist_all_complete(self, temp_state_dir, clear_state_before, capsys):
        """Test showing a checklist with all items complete."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(
            items=[
                ChecklistItem(id=1, text="Task 1", completed=True),
                ChecklistItem(id=2, text="Task 2", completed=True),
            ]
        )
        save_checklist(checklist)

        commands.show_checklist_cmd()

        captured = capsys.readouterr()
        assert "IMPLEMENTATION CHECKLIST (2/2 complete)" in captured.out
        assert "All items complete" in captured.out


class TestSetupWorktreeBackgroundCmd:
    """Tests for setup_worktree_background_cmd function."""

    def test_basic_invocation(self, temp_state_dir, clear_state_before):
        """Test basic command invocation with required args."""
        with patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_in_background_sync") as mock_setup:
            commands.setup_worktree_background_cmd(_argv=["--issue-key", "DFLY-1234"])

        mock_setup.assert_called_once_with(
            issue_key="DFLY-1234",
            branch_prefix="feature",
            workflow_name="work-on-jira-issue",
            user_request=None,
            additional_params=None,
        )

    def test_with_all_options(self, temp_state_dir, clear_state_before):
        """Test command with all options provided."""
        with patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_in_background_sync") as mock_setup:
            commands.setup_worktree_background_cmd(
                _argv=[
                    "--issue-key",
                    "DFLY-1234",
                    "--branch-prefix",
                    "bugfix",
                    "--workflow-name",
                    "custom-workflow",
                    "--user-request",
                    "My request",
                    "--additional-params",
                    '{"key": "value"}',
                ]
            )

        mock_setup.assert_called_once_with(
            issue_key="DFLY-1234",
            branch_prefix="bugfix",
            workflow_name="custom-workflow",
            user_request="My request",
            additional_params={"key": "value"},
        )

    def test_with_invalid_json_params(self, temp_state_dir, clear_state_before, capsys):
        """Test command handles invalid JSON in additional-params."""
        with patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_in_background_sync") as mock_setup:
            commands.setup_worktree_background_cmd(
                _argv=[
                    "--issue-key",
                    "DFLY-1234",
                    "--additional-params",
                    "not-valid-json",
                ]
            )

        # Should still call setup but with None for additional_params
        mock_setup.assert_called_once()
        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["additional_params"] is None

        captured = capsys.readouterr()
        assert "Could not parse additional-params JSON" in captured.err


class TestExecuteRetrieveStep:
    """Tests for _execute_retrieve_step function."""

    def test_get_issue_failure(self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys):
        """Test handling of get_issue failure (SystemExit)."""
        workflow_dir = temp_prompts_dir / "work-on-jira-issue"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-planning-prompt.md"
        template_file.write_text("Planning for {{issue_key}}", encoding="utf-8")

        with patch("agentic_devtools.cli.jira.get_commands.get_issue") as mock_get_issue:
            mock_get_issue.side_effect = SystemExit(1)

            commands._execute_retrieve_step("DFLY-1234", "feature/DFLY-1234/test")

        captured = capsys.readouterr()
        assert "Warning: Failed to fetch issue DFLY-1234" in captured.err

    def test_get_issue_exception(self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys):
        """Test handling of general exception when calling get_issue."""
        workflow_dir = temp_prompts_dir / "work-on-jira-issue"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-planning-prompt.md"
        template_file.write_text("Planning for {{issue_key}}", encoding="utf-8")

        with patch("agentic_devtools.cli.jira.get_commands.get_issue") as mock_get_issue:
            mock_get_issue.side_effect = Exception("Connection failed")

            commands._execute_retrieve_step("DFLY-1234", "feature/DFLY-1234/test")

        captured = capsys.readouterr()
        assert "Warning: Could not fetch Jira issue" in captured.err

    def test_formats_recent_comments(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test that recent comments are formatted correctly."""
        import json

        workflow_dir = temp_prompts_dir / "work-on-jira-issue"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-planning-prompt.md"
        template_file.write_text("Planning for {{issue_key}}", encoding="utf-8")

        # Set up issue data in temp file (new implementation reads from file, not state)
        issue_data = {
            "fields": {
                "summary": "Test issue",
                "issuetype": {"name": "Task"},
                "labels": [],
                "description": "Test description",
                "comment": {
                    "comments": [
                        {"author": {"displayName": "User 1"}, "body": "First comment"},
                        {"author": {"displayName": "User 2"}, "body": "Second comment"},
                    ]
                },
            }
        }
        issue_file = temp_state_dir / "temp-get-issue-details-response.json"
        issue_file.write_text(json.dumps(issue_data), encoding="utf-8")

        with patch("agentic_devtools.cli.jira.get_commands.get_issue") as mock_get_issue:
            # get_issue is called but we pre-populated the file
            mock_get_issue.return_value = None

            commands._execute_retrieve_step("DFLY-1234", "feature/DFLY-1234/test")

        captured = capsys.readouterr()
        assert "Issue DFLY-1234 retrieved successfully" in captured.out
