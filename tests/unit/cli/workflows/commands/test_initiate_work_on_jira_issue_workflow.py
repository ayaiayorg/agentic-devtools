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

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_work_on_jira_issue_workflow(_argv=["--interactive", "true"])

        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["interactive"] is True

    def test_interactive_defaults_to_false(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that interactive defaults to False when not specified."""
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
                issue_key="PROJECT-5555",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_work_on_jira_issue_workflow(_argv=["--issue-key", "PROJECT-5555"])

        # Verify the preflight was called with the CLI-provided issue key
        mock_preflight.assert_called_once_with("PROJECT-5555")

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

    def test_model_parsed_from_cli(self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys):
        """--model CLI arg overrides the default model."""
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

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_work_on_jira_issue_workflow(_argv=["--model", "gpt-4"])

        assert state.get_value("copilot.model_id") == "gpt-4"

    def test_programmatic_whitespace_model_falls_back_to_default(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Programmatic model='   ' is normalized to None and falls back to default."""
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

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                with patch(
                    "agentic_devtools.cli.workflows.commands.get_default_copilot_model",
                    return_value="gpt-4o",
                ):
                    mock_setup.return_value = True
                    commands.initiate_work_on_jira_issue_workflow(model="   ")

        assert state.get_value("copilot.model_id") == "gpt-4o"

    def test_auto_execute_command_includes_interactive_flag(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Test that auto_execute_command includes --interactive."""
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

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                with patch(
                    "agentic_devtools.cli.workflows.commands.get_default_copilot_model",
                    return_value="gpt-4o",
                ):
                    mock_setup.return_value = True
                    commands.initiate_work_on_jira_issue_workflow(_argv=["--interactive", "true"])

        call_kwargs = mock_setup.call_args[1]
        expected_cmd = [
            "agdt-initiate-work-on-jira-issue-workflow",
            "--issue-key",
            "PROJECT-1234",
            "--interactive",
            "true",
            "--model",
            "gpt-4o",
            "--skip-copilot-session",
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
        state.set_value("jira.issue_key", "PROJECT-1234")

        # Mock pre-flight to fail (folder doesn't contain issue key)
        # Patch at commands module level where it's imported at top
        with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong-folder",
                branch_name="main",
                issue_key="PROJECT-1234",
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
        state.set_value("jira.issue_key", "PROJECT-1234")
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
                folder_name="PROJECT-1234",
                branch_name="feature/PROJECT-1234/test",
                issue_key="PROJECT-1234",
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
        assert "Planning work for PROJECT-1234" in captured.out

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


class TestSkipCopilotSession:
    """Tests for the --skip-copilot-session flag."""

    def _setup_and_mock_preflight_pass(self, issue_key, argv=None, skip_copilot_session=False):
        """Helper: run the command with preflight passing, return mock_session."""
        from agentic_devtools.cli.workflows.preflight import PreflightResult

        argv = argv or []
        state.set_value("jira.issue_key", issue_key)
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

        with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name=issue_key,
                branch_name=f"feature/{issue_key}/test",
                issue_key=issue_key,
            )
            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup"):
                with patch("agentic_devtools.cli.jira.get_commands.get_issue"):
                    with patch(
                        "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_work_on_jira_issue"
                    ) as mock_session:
                        with patch(
                            "agentic_devtools.cli.workflows.commands.get_default_copilot_model",
                            return_value="gpt-4o",
                        ):
                            commands.initiate_work_on_jira_issue_workflow(
                                _argv=argv,
                                skip_copilot_session=skip_copilot_session,
                            )
                            return mock_session

    def test_skip_copilot_session_programmatic(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
    ):
        """skip_copilot_session=True prevents copilot session from starting."""
        # Setup template for planning step
        workflow_dir = temp_prompts_dir / "work-on-jira-issue"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-planning-prompt.md"
        template_file.write_text("Planning work for {{issue_key}}: {{issue_summary}}", encoding="utf-8")

        mock_session = self._setup_and_mock_preflight_pass("PROJECT-1234", skip_copilot_session=True)
        mock_session.assert_not_called()

    def test_skip_copilot_session_cli_flag(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
    ):
        """--skip-copilot-session CLI flag prevents copilot session from starting."""
        workflow_dir = temp_prompts_dir / "work-on-jira-issue"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-planning-prompt.md"
        template_file.write_text("Planning work for {{issue_key}}: {{issue_summary}}", encoding="utf-8")

        mock_session = self._setup_and_mock_preflight_pass("PROJECT-1234", argv=["--skip-copilot-session"])
        mock_session.assert_not_called()


class TestEngineLangchainFlag:
    """Tests for --engine langchain and --use-langchain flags."""

    def test_engine_langchain_routes_to_langchain_runner(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """--engine langchain routes to run_langchain_workflow instead of existing workflow."""
        state.set_value("jira.issue_key", "PROJECT-1234")

        import agentic_devtools.orchestration.runner as runner_mod

        with patch.object(runner_mod, "run_langchain_workflow") as mock_runner:
            commands.initiate_work_on_jira_issue_workflow(_argv=["--engine", "langchain"])

        mock_runner.assert_called_once()
        call_args = mock_runner.call_args
        assert call_args[0][0] == "PROJECT-1234"
        assert call_args[1]["resume"] is False
        assert call_args[1]["resume_data"] is None

    def test_use_langchain_alias_routes_to_langchain_runner(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """--use-langchain is an alias for --engine langchain."""
        state.set_value("jira.issue_key", "PROJECT-1234")

        import agentic_devtools.orchestration.runner as runner_mod

        with patch.object(runner_mod, "run_langchain_workflow") as mock_runner:
            commands.initiate_work_on_jira_issue_workflow(_argv=["--use-langchain"])

        mock_runner.assert_called_once()
        call_kwargs = mock_runner.call_args[1]
        assert call_kwargs["resume"] is False

    def test_no_engine_flag_routes_to_existing_workflow(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """Without --engine flag, the existing workflow is used (not LangChain)."""
        state.set_value("jira.issue_key", "PROJECT-1234")

        import agentic_devtools.orchestration.runner as runner_mod

        with patch.object(runner_mod, "run_langchain_workflow") as mock_runner:
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
                    commands.initiate_work_on_jira_issue_workflow(_argv=[])

        # LangChain runner should NOT have been called
        mock_runner.assert_not_called()

    def test_resume_without_engine_langchain_exits(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """--resume without --engine langchain exits with error."""
        state.set_value("jira.issue_key", "PROJECT-1234")

        with pytest.raises(SystemExit) as exc_info:
            commands.initiate_work_on_jira_issue_workflow(_argv=["--resume"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--resume requires --engine langchain" in captured.err

    def test_resume_with_engine_langchain_passes_resume_flag(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """--resume with --engine langchain passes resume=True to runner."""
        state.set_value("jira.issue_key", "PROJECT-1234")

        import agentic_devtools.orchestration.runner as runner_mod

        with patch.object(runner_mod, "run_langchain_workflow") as mock_runner:
            commands.initiate_work_on_jira_issue_workflow(_argv=["--engine", "langchain", "--resume"])

        mock_runner.assert_called_once()
        call_kwargs = mock_runner.call_args[1]
        assert call_kwargs["resume"] is True

    def test_resume_data_without_resume_exits(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """--resume-data without --resume exits with error."""
        state.set_value("jira.issue_key", "PROJECT-1234")

        with pytest.raises(SystemExit) as exc_info:
            commands.initiate_work_on_jira_issue_workflow(
                _argv=["--engine", "langchain", "--resume-data", '{"completed": true}']
            )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--resume-data requires --resume" in captured.err

    def test_resume_data_invalid_json_exits(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """--resume-data with invalid JSON exits with error."""
        state.set_value("jira.issue_key", "PROJECT-1234")

        with pytest.raises(SystemExit) as exc_info:
            commands.initiate_work_on_jira_issue_workflow(
                _argv=["--engine", "langchain", "--resume", "--resume-data", "not-json"]
            )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not valid JSON" in captured.err

    def test_resume_data_non_object_exits(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """--resume-data with non-object JSON (e.g., array) exits with error."""
        state.set_value("jira.issue_key", "PROJECT-1234")

        with pytest.raises(SystemExit) as exc_info:
            commands.initiate_work_on_jira_issue_workflow(
                _argv=["--engine", "langchain", "--resume", "--resume-data", "[1, 2, 3]"]
            )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "must be a JSON object" in captured.err

    def test_resume_data_valid_json_passes_to_runner(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """--resume-data with valid JSON object passes parsed data to runner."""
        state.set_value("jira.issue_key", "PROJECT-1234")

        import agentic_devtools.orchestration.runner as runner_mod

        with patch.object(runner_mod, "run_langchain_workflow") as mock_runner:
            commands.initiate_work_on_jira_issue_workflow(
                _argv=[
                    "--engine",
                    "langchain",
                    "--resume",
                    "--resume-data",
                    '{"completed": true, "summary": "Work done"}',
                ]
            )

        mock_runner.assert_called_once()
        call_kwargs = mock_runner.call_args[1]
        assert call_kwargs["resume_data"] == {"completed": True, "summary": "Work done"}

    def test_auto_execute_command_preserves_engine_langchain(
        self, temp_state_dir, clear_state_before, mock_workflow_state_clearing, capsys
    ):
        """When engine=langchain, the LangChain runner is invoked."""
        state.set_value("jira.issue_key", "PROJECT-1234")

        import agentic_devtools.orchestration.runner as runner_mod

        with patch.object(runner_mod, "run_langchain_workflow") as mock_runner:
            commands.initiate_work_on_jira_issue_workflow(_argv=["--engine", "langchain"])

        # The LangChain path handles its own preflight internally
        mock_runner.assert_called_once()
