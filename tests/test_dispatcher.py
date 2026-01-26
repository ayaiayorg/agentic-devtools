"""
Tests for the smart dispatcher that enables repo-local detection.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import dispatcher


class TestGetRepoRoot:
    """Tests for get_repo_root function."""

    def test_returns_path_when_in_git_repo(self, tmp_path):
        """Test that get_repo_root returns the repo root when in a git repo."""
        # Create a fake git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=str(tmp_path) + "\n",
            )
            result = dispatcher.get_repo_root()

        assert result == tmp_path
        mock_run.assert_called_once()

    def test_returns_none_when_not_in_git_repo(self):
        """Test that get_repo_root returns None when not in a git repo."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=128,
                stdout="",
            )
            result = dispatcher.get_repo_root()

        assert result is None

    def test_returns_none_when_git_not_installed(self):
        """Test that get_repo_root returns None when git is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git not found")
            result = dispatcher.get_repo_root()

        assert result is None


class TestGetLocalVenvPython:
    """Tests for get_local_venv_python function."""

    def test_returns_python_path_when_venv_exists(self, tmp_path):
        """Test that get_local_venv_python returns the python path when venv exists."""
        # Create a fake venv structure
        venv_dir = tmp_path / ".dfly-venv"
        if sys.platform == "win32":
            python_dir = venv_dir / "Scripts"
            python_file = python_dir / "python.exe"
        else:
            python_dir = venv_dir / "bin"
            python_file = python_dir / "python"

        python_dir.mkdir(parents=True)
        python_file.touch()

        with patch.object(dispatcher, "get_repo_root", return_value=tmp_path):
            result = dispatcher.get_local_venv_python()

        assert result == python_file

    def test_returns_none_when_venv_does_not_exist(self, tmp_path):
        """Test that get_local_venv_python returns None when venv doesn't exist."""
        with patch.object(dispatcher, "get_repo_root", return_value=tmp_path):
            result = dispatcher.get_local_venv_python()

        assert result is None

    def test_returns_none_when_not_in_repo(self):
        """Test that get_local_venv_python returns None when not in a repo."""
        with patch.object(dispatcher, "get_repo_root", return_value=None):
            result = dispatcher.get_local_venv_python()

        assert result is None

    def test_returns_none_when_python_exe_missing(self, tmp_path):
        """Test that get_local_venv_python returns None when python exe is missing."""
        # Create venv dir but no python executable
        venv_dir = tmp_path / ".dfly-venv"
        venv_dir.mkdir()

        with patch.object(dispatcher, "get_repo_root", return_value=tmp_path):
            result = dispatcher.get_local_venv_python()

        assert result is None


class TestIsRunningFromLocalVenv:
    """Tests for is_running_from_local_venv function."""

    def test_returns_true_when_running_from_local_venv(self, tmp_path):
        """Test that is_running_from_local_venv returns True when in local venv."""
        venv_dir = tmp_path / ".dfly-venv"
        if sys.platform == "win32":
            python_path = venv_dir / "Scripts" / "python.exe"
        else:
            python_path = venv_dir / "bin" / "python"

        with patch.object(dispatcher, "get_repo_root", return_value=tmp_path):
            with patch.object(sys, "executable", str(python_path)):
                result = dispatcher.is_running_from_local_venv()

        assert result is True

    def test_returns_false_when_running_from_global_python(self, tmp_path):
        """Test that is_running_from_local_venv returns False when using global python."""
        with patch.object(dispatcher, "get_repo_root", return_value=tmp_path):
            with patch.object(sys, "executable", "/usr/bin/python3"):
                result = dispatcher.is_running_from_local_venv()

        assert result is False

    def test_returns_false_when_not_in_repo(self):
        """Test that is_running_from_local_venv returns False when not in a repo."""
        with patch.object(dispatcher, "get_repo_root", return_value=None):
            result = dispatcher.is_running_from_local_venv()

        assert result is False


class TestDispatchToLocalVenv:
    """Tests for dispatch_to_local_venv function."""

    def test_returns_false_when_already_in_local_venv(self, tmp_path):
        """Test that dispatch returns False when already in local venv."""
        with patch.object(dispatcher, "is_running_from_local_venv", return_value=True):
            result = dispatcher.dispatch_to_local_venv("dfly-set")

        assert result is False

    def test_returns_false_when_no_local_venv(self, tmp_path):
        """Test that dispatch returns False when no local venv exists."""
        with patch.object(dispatcher, "is_running_from_local_venv", return_value=False):
            with patch.object(dispatcher, "get_local_venv_python", return_value=None):
                result = dispatcher.dispatch_to_local_venv("dfly-set")

        assert result is False

    def test_dispatches_to_local_venv_when_available(self, tmp_path):
        """Test that dispatch executes command in local venv when available."""
        local_python = tmp_path / ".dfly-venv" / "Scripts" / "python.exe"

        with patch.object(dispatcher, "is_running_from_local_venv", return_value=False):
            with patch.object(dispatcher, "get_local_venv_python", return_value=local_python):
                with patch("subprocess.run") as mock_run:
                    with patch.object(sys, "argv", ["dfly-set", "key", "value"]):
                        with pytest.raises(SystemExit) as exc_info:
                            mock_run.return_value = MagicMock(returncode=0)
                            dispatcher.dispatch_to_local_venv("dfly-set")

        assert exc_info.value.code == 0
        mock_run.assert_called_once()
        # Verify it called the runner module
        call_args = mock_run.call_args[0][0]
        assert str(local_python) in call_args[0]
        assert "agentic_devtools.cli.runner" in call_args
        assert "dfly-set" in call_args

    def test_returns_false_on_dispatch_error(self, tmp_path):
        """Test that dispatch returns False when subprocess fails."""
        local_python = tmp_path / ".dfly-venv" / "Scripts" / "python.exe"

        with patch.object(dispatcher, "is_running_from_local_venv", return_value=False):
            with patch.object(dispatcher, "get_local_venv_python", return_value=local_python):
                with patch("subprocess.run") as mock_run:
                    mock_run.side_effect = FileNotFoundError("python not found")
                    result = dispatcher.dispatch_to_local_venv("dfly-set")

        assert result is False


class TestCreateDispatcher:
    """Tests for create_dispatcher function."""

    def test_creates_callable_dispatcher(self):
        """Test that create_dispatcher returns a callable."""
        dispatcher_func = dispatcher.create_dispatcher("dfly-test", "agentic_devtools.cli.state", "show_cmd")
        assert callable(dispatcher_func)

    def test_dispatcher_calls_original_when_no_local_venv(self):
        """Test that dispatcher calls original function when no local venv."""
        mock_original = MagicMock()

        with patch.object(dispatcher, "dispatch_to_local_venv", return_value=False):
            with patch("importlib.import_module") as mock_import:
                mock_module = MagicMock()
                mock_module.test_func = mock_original
                mock_import.return_value = mock_module

                dispatcher_func = dispatcher.create_dispatcher("dfly-test", "test_module", "test_func")
                dispatcher_func()

        mock_original.assert_called_once()

    def test_dispatcher_handles_keyboard_interrupt(self):
        """Test that dispatcher handles KeyboardInterrupt gracefully."""
        with patch.object(dispatcher, "dispatch_to_local_venv", return_value=False):
            with patch("importlib.import_module") as mock_import:
                mock_import.side_effect = KeyboardInterrupt()

                dispatcher_func = dispatcher.create_dispatcher("dfly-test", "test_module", "test_func")
                with pytest.raises(SystemExit) as exc_info:
                    dispatcher_func()

        assert exc_info.value.code == 130  # Standard SIGINT exit code


class TestDispatcherEntryPoints:
    """Tests for the actual entry point dispatcher functions."""

    def test_set_cmd_is_callable(self):
        """Test that set_cmd dispatcher is callable."""
        assert callable(dispatcher.set_cmd)

    def test_get_cmd_is_callable(self):
        """Test that get_cmd dispatcher is callable."""
        assert callable(dispatcher.get_cmd)

    def test_show_cmd_is_callable(self):
        """Test that show_cmd dispatcher is callable."""
        assert callable(dispatcher.show_cmd)

    def test_commit_async_is_callable(self):
        """Test that commit_async (dfly-git-save-work) dispatcher is callable."""
        assert callable(dispatcher.commit_async)

    def test_get_issue_async_is_callable(self):
        """Test that get_issue_async (dfly-get-jira-issue) dispatcher is callable."""
        assert callable(dispatcher.get_issue_async)

    def test_delete_cmd_is_callable(self):
        """Test that delete_cmd dispatcher is callable."""
        assert callable(dispatcher.delete_cmd)

    def test_clear_cmd_is_callable(self):
        """Test that clear_cmd dispatcher is callable."""
        assert callable(dispatcher.clear_cmd)

    def test_get_workflow_cmd_is_callable(self):
        """Test that get_workflow_cmd dispatcher is callable."""
        assert callable(dispatcher.get_workflow_cmd)

    def test_clear_workflow_cmd_is_callable(self):
        """Test that clear_workflow_cmd dispatcher is callable."""
        assert callable(dispatcher.clear_workflow_cmd)

    def test_add_pull_request_comment_async_is_callable(self):
        """Test that add_pull_request_comment_async dispatcher is callable."""
        assert callable(dispatcher.add_pull_request_comment_async)

    def test_approve_pull_request_async_is_callable(self):
        """Test that approve_pull_request_async dispatcher is callable."""
        assert callable(dispatcher.approve_pull_request_async)

    def test_create_pull_request_async_cli_is_callable(self):
        """Test that create_pull_request_async_cli dispatcher is callable."""
        assert callable(dispatcher.create_pull_request_async_cli)

    def test_get_pull_request_threads_async_is_callable(self):
        """Test that get_pull_request_threads_async dispatcher is callable."""
        assert callable(dispatcher.get_pull_request_threads_async)

    def test_reply_to_pull_request_thread_async_is_callable(self):
        """Test that reply_to_pull_request_thread_async dispatcher is callable."""
        assert callable(dispatcher.reply_to_pull_request_thread_async)

    def test_resolve_thread_async_is_callable(self):
        """Test that resolve_thread_async dispatcher is callable."""
        assert callable(dispatcher.resolve_thread_async)

    def test_amend_async_is_callable(self):
        """Test that commit_async dispatcher is callable (handles --amend)."""
        assert callable(dispatcher.commit_async)

    def test_stage_async_is_callable(self):
        """Test that stage_async dispatcher is callable."""
        assert callable(dispatcher.stage_async)

    def test_push_async_is_callable(self):
        """Test that push_async dispatcher is callable."""
        assert callable(dispatcher.push_async)

    def test_force_push_async_is_callable(self):
        """Test that force_push_async dispatcher is callable."""
        assert callable(dispatcher.force_push_async)

    def test_publish_async_is_callable(self):
        """Test that publish_async dispatcher is callable."""
        assert callable(dispatcher.publish_async)

    def test_add_comment_async_cli_is_callable(self):
        """Test that add_comment_async_cli dispatcher is callable."""
        assert callable(dispatcher.add_comment_async_cli)

    def test_create_epic_async_is_callable(self):
        """Test that create_epic_async dispatcher is callable."""
        assert callable(dispatcher.create_epic_async)

    def test_create_issue_async_is_callable(self):
        """Test that create_issue_async dispatcher is callable."""
        assert callable(dispatcher.create_issue_async)

    def test_create_subtask_async_is_callable(self):
        """Test that create_subtask_async dispatcher is callable."""
        assert callable(dispatcher.create_subtask_async)

    def test_update_issue_async_is_callable(self):
        """Test that update_issue_async dispatcher is callable."""
        assert callable(dispatcher.update_issue_async)

    def test_initiate_work_on_jira_issue_workflow_is_callable(self):
        """Test that initiate_work_on_jira_issue_workflow dispatcher is callable."""
        assert callable(dispatcher.initiate_work_on_jira_issue_workflow)

    def test_get_next_workflow_prompt_cmd_is_callable(self):
        """Test that get_next_workflow_prompt_cmd dispatcher is callable."""
        assert callable(dispatcher.get_next_workflow_prompt_cmd)

    def test_setup_worktree_background_cmd_is_callable(self):
        """Test that setup_worktree_background_cmd dispatcher is callable."""
        assert callable(dispatcher.setup_worktree_background_cmd)

    def test_advance_workflow_cmd_is_callable(self):
        """Test that advance_workflow_cmd dispatcher is callable."""
        assert callable(dispatcher.advance_workflow_cmd)


# List of all entry point functions that delegate to create_dispatcher
# Excludes utility functions: create_dispatcher, dispatch_to_local_venv,
# get_local_venv_python, get_repo_root, is_running_from_local_venv
ENTRY_POINT_FUNCTIONS = [
    "add_comment_async_cli",
    "add_pull_request_comment_async",
    "add_users_to_project_role_async",
    "add_users_to_project_role_batch_async",
    "advance_workflow_cmd",
    "approve_file_async_cli",
    "approve_pull_request_async",
    "check_user_exists_async",
    "check_users_exist_async",
    "clear_cmd",
    "clear_workflow_cmd",
    "commit_async",
    "create_checklist_cmd",
    "create_epic_async",
    "create_issue_async",
    "create_pull_request_async_cli",
    "create_subtask_async",
    "delete_cmd",
    "find_role_id_by_name_async",
    "force_push_async",
    "generate_pr_summary_async",
    "get_cmd",
    "get_issue_async",
    "get_next_workflow_prompt_cmd",
    "get_project_role_details_async",
    "get_pull_request_details_async",
    "get_pull_request_threads_async",
    "get_run_details_async",
    "get_workflow_cmd",
    "initiate_apply_pull_request_review_suggestions_workflow",
    "initiate_create_jira_epic_workflow",
    "initiate_create_jira_issue_workflow",
    "initiate_create_jira_subtask_workflow",
    "initiate_pull_request_review_workflow",
    "initiate_update_jira_issue_workflow",
    "initiate_work_on_jira_issue_workflow",
    "list_project_roles_async",
    "list_tasks",
    "mark_file_reviewed_async",
    "mark_pull_request_draft_async",
    "parse_jira_error_report",
    "publish_async",
    "publish_pull_request_async",
    "push_async",
    "reply_to_pull_request_thread_async",
    "request_changes_async_cli",
    "request_changes_with_suggestion_async_cli",
    "resolve_thread_async",
    "run_e2e_tests_fabric_async",
    "run_e2e_tests_synapse_async",
    "run_tests",
    "run_tests_file",
    "run_tests_pattern",
    "run_tests_quick",
    "run_wb_patch_async",
    "set_cmd",
    "setup_worktree_background_cmd",
    "show_checklist_cmd",
    "show_cmd",
    "show_other_incomplete_tasks",
    "stage_async",
    "submit_file_review_async",
    "sync_async",
    "task_log",
    "task_status",
    "task_wait",
    "tasks_clean",
    "update_checklist_cmd",
    "update_issue_async",
]


class TestEntryPointFunctionExecution:
    """Tests that verify entry point functions execute their dispatcher logic.

    These are parametrized tests that ensure each entry point:
    1. Calls create_dispatcher with some arguments
    2. Calls the returned dispatcher function
    """

    @pytest.mark.parametrize("func_name", ENTRY_POINT_FUNCTIONS)
    def test_entry_point_calls_create_dispatcher_and_invokes_result(self, func_name):
        """Test that entry point function creates and invokes a dispatcher."""
        with patch.object(dispatcher, "create_dispatcher") as mock_create:
            mock_dispatcher = MagicMock()
            mock_create.return_value = mock_dispatcher

            # Get and call the entry point function
            entry_point_func = getattr(dispatcher, func_name)
            entry_point_func()

            # Verify create_dispatcher was called exactly once
            mock_create.assert_called_once()
            # Verify the returned dispatcher was invoked
            mock_dispatcher.assert_called_once()
