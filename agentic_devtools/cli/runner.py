"""
Command runner for agentic-devtools.

This module provides a way to run agdt-* commands by name, used by the
wrapper scripts (dfly.ps1, dfly.sh) that auto-detect the repo's local venv.

Usage:
    python -m agentic_devtools.cli.runner dfly-set key value
    python -m agentic_devtools.cli.runner dfly-get key
"""

import sys

# Map command names to their entry point functions
# This mirrors pyproject.toml [project.scripts]
COMMAND_MAP = {
    # State management
    "dfly-set": ("agentic_devtools.cli.state", "set_cmd"),
    "dfly-get": ("agentic_devtools.cli.state", "get_cmd"),
    "dfly-delete": ("agentic_devtools.cli.state", "delete_cmd"),
    "dfly-clear": ("agentic_devtools.cli.state", "clear_cmd"),
    "dfly-show": ("agentic_devtools.cli.state", "show_cmd"),
    # Workflow state
    "dfly-get-workflow": ("agentic_devtools.cli.state", "get_workflow_cmd"),
    "dfly-clear-workflow": ("agentic_devtools.cli.state", "clear_workflow_cmd"),
    # Azure DevOps
    "dfly-add-pull-request-comment": (
        "agentic_devtools.cli.azure_devops",
        "add_pull_request_comment_async",
    ),
    "dfly-approve-pull-request": (
        "agentic_devtools.cli.azure_devops",
        "approve_pull_request_async",
    ),
    "dfly-create-pull-request": (
        "agentic_devtools.cli.azure_devops",
        "create_pull_request_async_cli",
    ),
    "dfly-get-pull-request-threads": (
        "agentic_devtools.cli.azure_devops",
        "get_pull_request_threads_async",
    ),
    "dfly-reply-to-pull-request-thread": (
        "agentic_devtools.cli.azure_devops",
        "reply_to_pull_request_thread_async",
    ),
    "dfly-resolve-thread": (
        "agentic_devtools.cli.azure_devops",
        "resolve_thread_async",
    ),
    "dfly-mark-pull-request-draft": (
        "agentic_devtools.cli.azure_devops",
        "mark_pull_request_draft_async",
    ),
    "dfly-publish-pull-request": (
        "agentic_devtools.cli.azure_devops",
        "publish_pull_request_async",
    ),
    "dfly-run-e2e-tests-synapse": (
        "agentic_devtools.cli.azure_devops",
        "run_e2e_tests_synapse_async",
    ),
    "dfly-run-e2e-tests-fabric": (
        "agentic_devtools.cli.azure_devops",
        "run_e2e_tests_fabric_async",
    ),
    "dfly-run-wb-patch": (
        "agentic_devtools.cli.azure_devops",
        "run_wb_patch_async",
    ),
    "dfly-get-run-details": (
        "agentic_devtools.cli.azure_devops",
        "get_run_details_async",
    ),
    "dfly-wait-for-run": (
        "agentic_devtools.cli.azure_devops",
        "wait_for_run_async",
    ),
    "dfly-list-pipelines": (
        "agentic_devtools.cli.azure_devops",
        "list_pipelines_async",
    ),
    "dfly-get-pipeline-id": (
        "agentic_devtools.cli.azure_devops",
        "get_pipeline_id_async",
    ),
    "dfly-create-pipeline": (
        "agentic_devtools.cli.azure_devops",
        "create_pipeline_async",
    ),
    "dfly-update-pipeline": (
        "agentic_devtools.cli.azure_devops",
        "update_pipeline_async",
    ),
    "dfly-get-pull-request-details": (
        "agentic_devtools.cli.azure_devops",
        "get_pull_request_details_async",
    ),
    "dfly-approve-file": (
        "agentic_devtools.cli.azure_devops",
        "approve_file_async_cli",
    ),
    "dfly-submit-file-review": (
        "agentic_devtools.cli.azure_devops",
        "submit_file_review_async",
    ),
    "dfly-request-changes": (
        "agentic_devtools.cli.azure_devops",
        "request_changes_async_cli",
    ),
    "dfly-request-changes-with-suggestion": (
        "agentic_devtools.cli.azure_devops",
        "request_changes_with_suggestion_async_cli",
    ),
    "dfly-mark-file-reviewed": (
        "agentic_devtools.cli.azure_devops",
        "mark_file_reviewed_async",
    ),
    "dfly-generate-pr-summary": (
        "agentic_devtools.cli.azure_devops",
        "generate_pr_summary_async",
    ),
    # VPN Toggle (all run in background)
    "dfly-vpn-off": (
        "agentic_devtools.cli.azure_devops.vpn_toggle",
        "vpn_off_async",
    ),
    "dfly-vpn-on": (
        "agentic_devtools.cli.azure_devops.vpn_toggle",
        "vpn_on_async",
    ),
    "dfly-vpn-status": (
        "agentic_devtools.cli.azure_devops.vpn_toggle",
        "vpn_status_async",
    ),
    # Jira
    "dfly-create-epic": ("agentic_devtools.cli.jira", "create_epic_async"),
    "dfly-create-issue": ("agentic_devtools.cli.jira", "create_issue_async"),
    "dfly-create-subtask": ("agentic_devtools.cli.jira", "create_subtask_async"),
    "dfly-add-jira-comment": ("agentic_devtools.cli.jira", "add_comment_async_cli"),
    "dfly-get-jira-issue": ("agentic_devtools.cli.jira", "get_issue_async"),
    "dfly-update-jira-issue": ("agentic_devtools.cli.jira", "update_issue_async"),
    "dfly-list-project-roles": (
        "agentic_devtools.cli.jira",
        "list_project_roles_async",
    ),
    "dfly-get-project-role-details": (
        "agentic_devtools.cli.jira",
        "get_project_role_details_async",
    ),
    "dfly-add-users-to-project-role": (
        "agentic_devtools.cli.jira",
        "add_users_to_project_role_async",
    ),
    "dfly-add-users-to-project-role-batch": (
        "agentic_devtools.cli.jira",
        "add_users_to_project_role_batch_async",
    ),
    "dfly-find-role-id-by-name": (
        "agentic_devtools.cli.jira",
        "find_role_id_by_name_async",
    ),
    "dfly-check-user-exists": (
        "agentic_devtools.cli.jira",
        "check_user_exists_async",
    ),
    "dfly-check-users-exist": (
        "agentic_devtools.cli.jira",
        "check_users_exist_async",
    ),
    "dfly-parse-jira-error-report": (
        "agentic_devtools.cli.jira",
        "parse_jira_error_report",
    ),
    # Git
    "dfly-git-save-work": ("agentic_devtools.cli.git", "commit_async"),
    "dfly-git-sync": ("agentic_devtools.cli.git", "sync_async"),
    "dfly-git-stage": ("agentic_devtools.cli.git", "stage_async"),
    "dfly-git-push": ("agentic_devtools.cli.git", "push_async"),
    "dfly-git-force-push": ("agentic_devtools.cli.git", "force_push_async"),
    "dfly-git-publish": ("agentic_devtools.cli.git", "publish_async"),
    # Testing
    "dfly-test": ("agentic_devtools.cli.testing", "run_tests"),
    "dfly-test-quick": ("agentic_devtools.cli.testing", "run_tests_quick"),
    "dfly-test-file": ("agentic_devtools.cli.testing", "run_tests_file"),
    "dfly-test-pattern": ("agentic_devtools.cli.testing", "run_tests_pattern"),
    # Tasks
    "dfly-tasks": ("agentic_devtools.cli.tasks", "list_tasks"),
    "dfly-task-status": ("agentic_devtools.cli.tasks", "task_status"),
    "dfly-task-log": ("agentic_devtools.cli.tasks", "task_log"),
    "dfly-task-wait": ("agentic_devtools.cli.tasks", "task_wait"),
    "dfly-tasks-clean": ("agentic_devtools.cli.tasks", "tasks_clean"),
    "dfly-show-other-incomplete-tasks": (
        "agentic_devtools.cli.tasks",
        "show_other_incomplete_tasks",
    ),
    # Workflows
    "dfly-initiate-pull-request-review-workflow": (
        "agentic_devtools.cli.workflows",
        "initiate_pull_request_review_workflow",
    ),
    "dfly-initiate-work-on-jira-issue-workflow": (
        "agentic_devtools.cli.workflows",
        "initiate_work_on_jira_issue_workflow",
    ),
    "dfly-initiate-create-jira-issue-workflow": (
        "agentic_devtools.cli.workflows",
        "initiate_create_jira_issue_workflow",
    ),
    "dfly-initiate-create-jira-epic-workflow": (
        "agentic_devtools.cli.workflows",
        "initiate_create_jira_epic_workflow",
    ),
    "dfly-initiate-create-jira-subtask-workflow": (
        "agentic_devtools.cli.workflows",
        "initiate_create_jira_subtask_workflow",
    ),
    "dfly-initiate-update-jira-issue-workflow": (
        "agentic_devtools.cli.workflows",
        "initiate_update_jira_issue_workflow",
    ),
    "dfly-initiate-apply-pr-suggestions-workflow": (
        "agentic_devtools.cli.workflows",
        "initiate_apply_pull_request_review_suggestions_workflow",
    ),
    "dfly-advance-workflow": (
        "agentic_devtools.cli.workflows",
        "advance_workflow_cmd",
    ),
    "dfly-get-next-workflow-prompt": (
        "agentic_devtools.cli.workflows",
        "get_next_workflow_prompt_cmd",
    ),
    "dfly-create-checklist": (
        "agentic_devtools.cli.workflows",
        "create_checklist_cmd",
    ),
    "dfly-update-checklist": (
        "agentic_devtools.cli.workflows",
        "update_checklist_cmd",
    ),
    "dfly-show-checklist": (
        "agentic_devtools.cli.workflows",
        "show_checklist_cmd",
    ),
    # Background worktree setup (internal, called by background task)
    "dfly-setup-worktree-background": (
        "agentic_devtools.cli.workflows",
        "setup_worktree_background_cmd",
    ),
}


def run_command(command: str) -> None:
    """
    Import and run the specified command.

    Args:
        command: The agdt-* command name (e.g., 'agdt-set', 'agdt-get')
    """
    if command not in COMMAND_MAP:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("\nAvailable commands:", file=sys.stderr)
        for cmd in sorted(COMMAND_MAP.keys()):
            print(f"  {cmd}", file=sys.stderr)
        sys.exit(1)

    module_name, func_name = COMMAND_MAP[command]

    # Import the module and get the function
    import importlib

    try:
        module = importlib.import_module(module_name)
        func = getattr(module, func_name)
    except (ImportError, AttributeError) as e:
        print(f"Error loading command {command}: {e}", file=sys.stderr)
        sys.exit(1)

    # Run the command
    func()


def main() -> None:
    """
    Main entry point for the runner.

    Parses the command name from arguments and dispatches to the appropriate
    entry point function.
    """
    if len(sys.argv) < 2:
        print("Usage: python -m agentic_devtools.cli.runner <command> [args...]")
        print()
        print("Example: python -m agentic_devtools.cli.runner dfly-set key value")
        print()
        print("Available commands:")
        for cmd in sorted(COMMAND_MAP.keys()):
            print(f"  {cmd}")
        sys.exit(1)

    command = sys.argv[1]

    # Remove the command from argv so the actual command sees correct args
    sys.argv = [command] + sys.argv[2:]

    try:
        run_command(command)
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        sys.exit(130)  # Standard exit code for SIGINT


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        sys.exit(130)
