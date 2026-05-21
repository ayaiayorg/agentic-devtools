"""Tests for --engine and --use-langchain routing in initiate_pull_request_review_workflow."""

from unittest.mock import patch

from agentic_devtools.cli.workflows import commands


class TestEngineLangchainRouting:
    """Tests for LangChain engine routing via --engine and --use-langchain flags."""

    def _run_with_engine_flag(self, engine_flag=None, use_langchain=False, pr_id="123"):
        """Helper to invoke initiate_pull_request_review_workflow with engine flags."""
        argv = ["--pull-request-id", pr_id]
        if engine_flag:
            argv.extend(["--engine", engine_flag])
        if use_langchain:
            argv.append("--use-langchain")

        with patch("agentic_devtools.cli.workflows.commands._ensure_bootstrap_identity_and_scope"):
            with patch("agentic_devtools.state.get_state_dir") as mock_state_dir:
                import tempfile
                from pathlib import Path

                tmp = tempfile.mkdtemp()
                mock_state_dir.return_value = Path(tmp)
                with patch("agentic_devtools.cli.workflows.commands.get_state_dir", return_value=Path(tmp)):
                    with patch("agentic_devtools.state.delete_pin_file"):
                        with patch("agentic_devtools.state.write_pin_file"):
                            with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
                                with patch("agentic_devtools.cli.workflows.commands.get_default_copilot_model", return_value="gpt-4o"):
                                    with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
                                        from agentic_devtools.cli.workflows.preflight import PreflightResult

                                        mock_preflight.return_value = PreflightResult(
                                            folder_valid=True,
                                            branch_valid=True,
                                            folder_name=f"PR{pr_id}",
                                            branch_name="feature/test",
                                            issue_key=None,
                                        )
                                        with patch("agentic_devtools.cli.azure_devops.helpers.get_pull_request_source_branch", return_value="feature/test"):
                                            with patch("agentic_devtools.cli.azure_devops.helpers.find_jira_issue_from_pr", return_value=None):
                                                with patch.dict("os.environ", {"AGENTIC_DEVTOOLS_STATE_DIR": tmp}):
                                                    with patch("agentic_devtools.orchestration.review.preflight.validate_langchain_dependencies", return_value=True) as mock_preflight_deps:
                                                        with patch("agentic_devtools.orchestration.review.runner.run_langchain_review") as mock_run:
                                                            mock_run.return_value = {"status": "completed", "decision": "approved"}
                                                            with patch("agentic_devtools.cli.azure_devops.async_commands.setup_pull_request_review_async") as mock_async:
                                                                with patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_pr_review") as mock_session:
                                                                    commands.initiate_pull_request_review_workflow(_argv=argv)
                                                                    return {
                                                                        "run_langchain": mock_run,
                                                                        "validate_deps": mock_preflight_deps,
                                                                        "async_setup": mock_async,
                                                                        "session": mock_session,
                                                                    }

    def test_engine_langchain_routes_to_langchain_path(self, tmp_path):
        """--engine langchain routes to the LangChain review pipeline."""
        mocks = self._run_with_engine_flag(engine_flag="langchain")
        mocks["run_langchain"].assert_called_once()
        # Default path should NOT be called
        mocks["async_setup"].assert_not_called()
        mocks["session"].assert_not_called()

    def test_use_langchain_flag_routes_to_langchain_path(self, tmp_path):
        """--use-langchain routes to the LangChain review pipeline."""
        mocks = self._run_with_engine_flag(use_langchain=True)
        mocks["run_langchain"].assert_called_once()
        mocks["async_setup"].assert_not_called()

    def test_default_engine_routes_to_existing_path(self, tmp_path):
        """No engine flag routes to the existing default path."""
        mocks = self._run_with_engine_flag()
        mocks["run_langchain"].assert_not_called()
        mocks["async_setup"].assert_called_once()
        mocks["session"].assert_called_once()

    def test_engine_default_explicitly_routes_to_existing_path(self, tmp_path):
        """--engine default explicitly routes to the existing path."""
        mocks = self._run_with_engine_flag(engine_flag="default")
        mocks["run_langchain"].assert_not_called()
        mocks["async_setup"].assert_called_once()

    def test_langchain_path_validates_dependencies(self, tmp_path):
        """LangChain path calls validate_langchain_dependencies."""
        mocks = self._run_with_engine_flag(engine_flag="langchain")
        mocks["validate_deps"].assert_called_once()

    def test_engine_default_with_use_langchain_emits_warning(self, tmp_path):
        """--engine default + --use-langchain emits a visible UserWarning."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mocks = self._run_with_engine_flag(engine_flag="default", use_langchain=True)
            # Should route to default path (--use-langchain ignored)
            mocks["run_langchain"].assert_not_called()
            mocks["async_setup"].assert_called_once()
            # Should have emitted a visible warning category
            user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
            assert len(user_warnings) >= 1
            assert "--use-langchain is ignored" in str(user_warnings[0].message)
