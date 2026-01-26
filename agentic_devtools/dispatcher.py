"""
Smart dispatcher for agentic-devtools that detects repo-local installations.

This module provides entry point wrappers that:
1. Detect the current git repository root
2. Check if that repo has a local .dfly-venv with agentic-devtools installed
3. If yes, delegate to that installation (re-exec with the local Python)
4. If no, run the command locally using the global installation

This enables multi-worktree development where each worktree can have its own
version of agentic-devtools while keeping the simple `dfly-*` command interface.
"""

import subprocess
import sys
from pathlib import Path

# Name of the local venv directory
DFLY_VENV_NAME = ".dfly-venv"


def get_repo_root() -> Path | None:
    """
    Get the git repository root for the current working directory.

    Returns:
        Path to the repo root, or None if not in a git repo.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
    except (FileNotFoundError, OSError):
        pass
    return None


def get_local_venv_python() -> Path | None:
    """
    Find the Python executable in the current repo's local venv.

    Returns:
        Path to the venv's Python executable, or None if not found.
    """
    repo_root = get_repo_root()
    if not repo_root:
        return None

    venv_path = repo_root / DFLY_VENV_NAME

    if not venv_path.exists():
        return None

    # Check for Python in the venv (Windows vs Unix paths)
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"

    if python_exe.exists():
        return python_exe

    return None


def is_running_from_local_venv() -> bool:
    """
    Check if we're already running from a repo-local .dfly-venv.

    This prevents infinite recursion when the local venv dispatches to itself.
    """
    current_exe = Path(sys.executable).resolve()
    repo_root = get_repo_root()

    if not repo_root:
        return False

    venv_path = (repo_root / DFLY_VENV_NAME).resolve()

    # Check if current Python is inside the local venv
    try:
        current_exe.relative_to(venv_path)
        return True
    except ValueError:
        return False


def dispatch_to_local_venv(command_name: str) -> bool:
    """
    Attempt to dispatch the command to a repo-local venv installation.

    Args:
        command_name: The dfly-* command name (e.g., 'dfly-set', 'dfly-get')

    Returns:
        True if dispatched (and this process should exit), False to run locally.
    """
    # Don't dispatch if we're already in the local venv
    if is_running_from_local_venv():
        return False

    local_python = get_local_venv_python()
    if not local_python:
        return False

    # Re-exec the command using the local venv's Python
    # Use the runner module to dispatch to the right entry point
    try:
        result = subprocess.run(
            [
                str(local_python),
                "-m",
                "agentic_devtools.cli.runner",
                command_name,
            ]
            + sys.argv[1:],
            check=False,
        )
        sys.exit(result.returncode)
    except (FileNotFoundError, OSError):
        # If dispatch fails, fall back to local execution
        return False

    return True


def create_dispatcher(command_name: str, module_name: str, func_name: str):
    """
    Create a dispatcher function for a dfly-* command.

    The dispatcher will:
    1. Try to delegate to a repo-local venv if one exists
    2. Fall back to running the command locally

    Args:
        command_name: The dfly-* command name (e.g., 'dfly-set')
        module_name: The module containing the actual implementation
        func_name: The function name to call

    Returns:
        A callable that can be used as an entry point.
    """

    def dispatcher():
        try:
            # Try to dispatch to local venv first
            if dispatch_to_local_venv(command_name):
                return  # Won't reach here - dispatch_to_local_venv exits

            # Run locally - import and call the actual function
            import importlib

            module = importlib.import_module(module_name)
            func = getattr(module, func_name)
            func()
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            sys.exit(130)  # Standard exit code for SIGINT

    return dispatcher


# =============================================================================
# Entry point dispatchers
# =============================================================================


# State management
def set_cmd():
    create_dispatcher("dfly-set", "agentic_devtools.cli.state", "set_cmd")()


def get_cmd():
    create_dispatcher("dfly-get", "agentic_devtools.cli.state", "get_cmd")()


def delete_cmd():
    create_dispatcher("dfly-delete", "agentic_devtools.cli.state", "delete_cmd")()


def clear_cmd():
    create_dispatcher("dfly-clear", "agentic_devtools.cli.state", "clear_cmd")()


def show_cmd():
    create_dispatcher("dfly-show", "agentic_devtools.cli.state", "show_cmd")()


def get_workflow_cmd():
    create_dispatcher("dfly-get-workflow", "agentic_devtools.cli.state", "get_workflow_cmd")()


def clear_workflow_cmd():
    create_dispatcher("dfly-clear-workflow", "agentic_devtools.cli.state", "clear_workflow_cmd")()


# Azure DevOps
def add_pull_request_comment_async():
    create_dispatcher(
        "dfly-add-pull-request-comment",
        "agentic_devtools.cli.azure_devops",
        "add_pull_request_comment_async",
    )()


def approve_pull_request_async():
    create_dispatcher(
        "dfly-approve-pull-request",
        "agentic_devtools.cli.azure_devops",
        "approve_pull_request_async",
    )()


def create_pull_request_async_cli():
    create_dispatcher(
        "dfly-create-pull-request",
        "agentic_devtools.cli.azure_devops",
        "create_pull_request_async_cli",
    )()


def get_pull_request_threads_async():
    create_dispatcher(
        "dfly-get-pull-request-threads",
        "agentic_devtools.cli.azure_devops",
        "get_pull_request_threads_async",
    )()


def reply_to_pull_request_thread_async():
    create_dispatcher(
        "dfly-reply-to-pull-request-thread",
        "agentic_devtools.cli.azure_devops",
        "reply_to_pull_request_thread_async",
    )()


def resolve_thread_async():
    create_dispatcher(
        "dfly-resolve-thread",
        "agentic_devtools.cli.azure_devops",
        "resolve_thread_async",
    )()


def mark_pull_request_draft_async():
    create_dispatcher(
        "dfly-mark-pull-request-draft",
        "agentic_devtools.cli.azure_devops",
        "mark_pull_request_draft_async",
    )()


def publish_pull_request_async():
    create_dispatcher(
        "dfly-publish-pull-request",
        "agentic_devtools.cli.azure_devops",
        "publish_pull_request_async",
    )()


def run_e2e_tests_synapse_async():
    create_dispatcher(
        "dfly-run-e2e-tests-synapse",
        "agentic_devtools.cli.azure_devops",
        "run_e2e_tests_synapse_async",
    )()


def run_e2e_tests_fabric_async():
    create_dispatcher(
        "dfly-run-e2e-tests-fabric",
        "agentic_devtools.cli.azure_devops",
        "run_e2e_tests_fabric_async",
    )()


def run_wb_patch_async():
    create_dispatcher(
        "dfly-run-wb-patch",
        "agentic_devtools.cli.azure_devops",
        "run_wb_patch_async",
    )()


def get_run_details_async():
    create_dispatcher(
        "dfly-get-run-details",
        "agentic_devtools.cli.azure_devops",
        "get_run_details_async",
    )()


def wait_for_run_async():
    create_dispatcher(
        "dfly-wait-for-run",
        "agentic_devtools.cli.azure_devops",
        "wait_for_run_async",
    )()


def list_pipelines_async():
    create_dispatcher(
        "dfly-list-pipelines",
        "agentic_devtools.cli.azure_devops",
        "list_pipelines_async",
    )()


def get_pipeline_id_async():
    create_dispatcher(
        "dfly-get-pipeline-id",
        "agentic_devtools.cli.azure_devops",
        "get_pipeline_id_async",
    )()


def create_pipeline_async():
    create_dispatcher(
        "dfly-create-pipeline",
        "agentic_devtools.cli.azure_devops",
        "create_pipeline_async",
    )()


def update_pipeline_async():
    create_dispatcher(
        "dfly-update-pipeline",
        "agentic_devtools.cli.azure_devops",
        "update_pipeline_async",
    )()


def get_pull_request_details_async():
    create_dispatcher(
        "dfly-get-pull-request-details",
        "agentic_devtools.cli.azure_devops",
        "get_pull_request_details_async",
    )()


def approve_file_async_cli():
    create_dispatcher(
        "dfly-approve-file",
        "agentic_devtools.cli.azure_devops",
        "approve_file_async_cli",
    )()


def submit_file_review_async():
    create_dispatcher(
        "dfly-submit-file-review",
        "agentic_devtools.cli.azure_devops",
        "submit_file_review_async",
    )()


def request_changes_async_cli():
    create_dispatcher(
        "dfly-request-changes",
        "agentic_devtools.cli.azure_devops",
        "request_changes_async_cli",
    )()


def request_changes_with_suggestion_async_cli():
    create_dispatcher(
        "dfly-request-changes-with-suggestion",
        "agentic_devtools.cli.azure_devops",
        "request_changes_with_suggestion_async_cli",
    )()


def mark_file_reviewed_async():
    create_dispatcher(
        "dfly-mark-file-reviewed",
        "agentic_devtools.cli.azure_devops",
        "mark_file_reviewed_async",
    )()


def generate_pr_summary_async():
    create_dispatcher(
        "dfly-generate-pr-summary",
        "agentic_devtools.cli.azure_devops",
        "generate_pr_summary_async",
    )()


# Jira
def create_epic_async():
    create_dispatcher("dfly-create-epic", "agentic_devtools.cli.jira", "create_epic_async")()


def create_issue_async():
    create_dispatcher("dfly-create-issue", "agentic_devtools.cli.jira", "create_issue_async")()


def create_subtask_async():
    create_dispatcher("dfly-create-subtask", "agentic_devtools.cli.jira", "create_subtask_async")()


def add_comment_async_cli():
    create_dispatcher("dfly-add-jira-comment", "agentic_devtools.cli.jira", "add_comment_async_cli")()


def get_issue_async():
    create_dispatcher("dfly-get-jira-issue", "agentic_devtools.cli.jira", "get_issue_async")()


def update_issue_async():
    create_dispatcher("dfly-update-jira-issue", "agentic_devtools.cli.jira", "update_issue_async")()


def list_project_roles_async():
    create_dispatcher("dfly-list-project-roles", "agentic_devtools.cli.jira", "list_project_roles_async")()


def get_project_role_details_async():
    create_dispatcher(
        "dfly-get-project-role-details",
        "agentic_devtools.cli.jira",
        "get_project_role_details_async",
    )()


def add_users_to_project_role_async():
    create_dispatcher(
        "dfly-add-users-to-project-role",
        "agentic_devtools.cli.jira",
        "add_users_to_project_role_async",
    )()


def add_users_to_project_role_batch_async():
    create_dispatcher(
        "dfly-add-users-to-project-role-batch",
        "agentic_devtools.cli.jira",
        "add_users_to_project_role_batch_async",
    )()


def find_role_id_by_name_async():
    create_dispatcher(
        "dfly-find-role-id-by-name",
        "agentic_devtools.cli.jira",
        "find_role_id_by_name_async",
    )()


def check_user_exists_async():
    create_dispatcher("dfly-check-user-exists", "agentic_devtools.cli.jira", "check_user_exists_async")()


def check_users_exist_async():
    create_dispatcher("dfly-check-users-exist", "agentic_devtools.cli.jira", "check_users_exist_async")()


def parse_jira_error_report():
    create_dispatcher(
        "dfly-parse-jira-error-report",
        "agentic_devtools.cli.jira",
        "parse_jira_error_report",
    )()


# Git
def commit_async():
    create_dispatcher("dfly-git-save-work", "agentic_devtools.cli.git", "commit_async")()


def sync_async():
    create_dispatcher("dfly-git-sync", "agentic_devtools.cli.git", "sync_async")()


def stage_async():
    create_dispatcher("dfly-git-stage", "agentic_devtools.cli.git", "stage_async")()


def push_async():
    create_dispatcher("dfly-git-push", "agentic_devtools.cli.git", "push_async")()


def force_push_async():
    create_dispatcher("dfly-git-force-push", "agentic_devtools.cli.git", "force_push_async")()


def publish_async():
    create_dispatcher("dfly-git-publish", "agentic_devtools.cli.git", "publish_async")()


# Testing
def run_tests():
    create_dispatcher("dfly-test", "agentic_devtools.cli.testing", "run_tests")()


def run_tests_quick():
    create_dispatcher("dfly-test-quick", "agentic_devtools.cli.testing", "run_tests_quick")()


def run_tests_file():
    create_dispatcher("dfly-test-file", "agentic_devtools.cli.testing", "run_tests_file")()


def run_tests_pattern():
    create_dispatcher("dfly-test-pattern", "agentic_devtools.cli.testing", "run_tests_pattern")()


# Tasks
def list_tasks():
    create_dispatcher("dfly-tasks", "agentic_devtools.cli.tasks", "list_tasks")()


def task_status():
    create_dispatcher("dfly-task-status", "agentic_devtools.cli.tasks", "task_status")()


def task_log():
    create_dispatcher("dfly-task-log", "agentic_devtools.cli.tasks", "task_log")()


def task_wait():
    create_dispatcher("dfly-task-wait", "agentic_devtools.cli.tasks", "task_wait")()


def tasks_clean():
    create_dispatcher("dfly-tasks-clean", "agentic_devtools.cli.tasks", "tasks_clean")()


def show_other_incomplete_tasks():
    create_dispatcher(
        "dfly-show-other-incomplete-tasks",
        "agentic_devtools.cli.tasks",
        "show_other_incomplete_tasks",
    )()


# Workflows
def initiate_pull_request_review_workflow():
    create_dispatcher(
        "dfly-initiate-pull-request-review-workflow",
        "agentic_devtools.cli.workflows",
        "initiate_pull_request_review_workflow",
    )()


def initiate_work_on_jira_issue_workflow():
    create_dispatcher(
        "dfly-initiate-work-on-jira-issue-workflow",
        "agentic_devtools.cli.workflows",
        "initiate_work_on_jira_issue_workflow",
    )()


def initiate_create_jira_issue_workflow():
    create_dispatcher(
        "dfly-initiate-create-jira-issue-workflow",
        "agentic_devtools.cli.workflows",
        "initiate_create_jira_issue_workflow",
    )()


def initiate_create_jira_epic_workflow():
    create_dispatcher(
        "dfly-initiate-create-jira-epic-workflow",
        "agentic_devtools.cli.workflows",
        "initiate_create_jira_epic_workflow",
    )()


def initiate_create_jira_subtask_workflow():
    create_dispatcher(
        "dfly-initiate-create-jira-subtask-workflow",
        "agentic_devtools.cli.workflows",
        "initiate_create_jira_subtask_workflow",
    )()


def initiate_update_jira_issue_workflow():
    create_dispatcher(
        "dfly-initiate-update-jira-issue-workflow",
        "agentic_devtools.cli.workflows",
        "initiate_update_jira_issue_workflow",
    )()


def initiate_apply_pull_request_review_suggestions_workflow():
    create_dispatcher(
        "dfly-initiate-apply-pr-suggestions-workflow",
        "agentic_devtools.cli.workflows",
        "initiate_apply_pull_request_review_suggestions_workflow",
    )()


def setup_worktree_background_cmd():
    create_dispatcher(
        "dfly-setup-worktree-background",
        "agentic_devtools.cli.workflows",
        "setup_worktree_background_cmd",
    )()


def advance_workflow_cmd():
    create_dispatcher("dfly-advance-workflow", "agentic_devtools.cli.workflows", "advance_workflow_cmd")()


def get_next_workflow_prompt_cmd():
    create_dispatcher(
        "dfly-get-next-workflow-prompt",
        "agentic_devtools.cli.workflows",
        "get_next_workflow_prompt_cmd",
    )()


def create_checklist_cmd():
    create_dispatcher("dfly-create-checklist", "agentic_devtools.cli.workflows", "create_checklist_cmd")()


def update_checklist_cmd():
    create_dispatcher("dfly-update-checklist", "agentic_devtools.cli.workflows", "update_checklist_cmd")()


def show_checklist_cmd():
    create_dispatcher("dfly-show-checklist", "agentic_devtools.cli.workflows", "show_checklist_cmd")()


# VPN toggle commands (all run in background)
def vpn_on_cmd():
    create_dispatcher("dfly-vpn-on", "agentic_devtools.cli.azure_devops.vpn_toggle", "vpn_on_async")()


def vpn_off_cmd():
    create_dispatcher("dfly-vpn-off", "agentic_devtools.cli.azure_devops.vpn_toggle", "vpn_off_async")()


def vpn_status_cmd():
    create_dispatcher("dfly-vpn-status", "agentic_devtools.cli.azure_devops.vpn_toggle", "vpn_status_async")()
