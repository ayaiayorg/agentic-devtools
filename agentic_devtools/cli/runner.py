"""
Command runner for agentic-devtools.

This module provides a way to run agdt-* commands by name, used by the
wrapper scripts (agdt.ps1, agdt.sh) that auto-detect the repo's local venv.

Usage:
    python -m agentic_devtools.cli.runner agdt-set key value
    python -m agentic_devtools.cli.runner agdt-get key
"""

import sys

# Map command names to their entry point functions
# This mirrors pyproject.toml [project.scripts]
COMMAND_MAP = {
    # State management
    "agdt-set": ("agentic_devtools.cli.state", "set_cmd"),
    "agdt-get": ("agentic_devtools.cli.state", "get_cmd"),
    "agdt-delete": ("agentic_devtools.cli.state", "delete_cmd"),
    "agdt-clear": ("agentic_devtools.cli.state", "clear_cmd"),
    "agdt-show": ("agentic_devtools.cli.state", "show_cmd"),
    # Workflow state
    "agdt-get-workflow": ("agentic_devtools.cli.state", "get_workflow_cmd"),
    "agdt-clear-workflow": ("agentic_devtools.cli.state", "clear_workflow_cmd"),
    # Azure DevOps
    "agdt-add-pull-request-comment": (
        "agentic_devtools.cli.azure_devops",
        "add_pull_request_comment_async",
    ),
    "agdt-approve-pull-request": (
        "agentic_devtools.cli.azure_devops",
        "approve_pull_request_async",
    ),
    "agdt-create-pull-request": (
        "agentic_devtools.cli.azure_devops",
        "create_pull_request_async_cli",
    ),
    "agdt-get-pull-request-threads": (
        "agentic_devtools.cli.azure_devops",
        "get_pull_request_threads_async",
    ),
    "agdt-reply-to-pull-request-thread": (
        "agentic_devtools.cli.azure_devops",
        "reply_to_pull_request_thread_async",
    ),
    "agdt-resolve-thread": (
        "agentic_devtools.cli.azure_devops",
        "resolve_thread_async",
    ),
    "agdt-mark-pull-request-draft": (
        "agentic_devtools.cli.azure_devops",
        "mark_pull_request_draft_async",
    ),
    "agdt-publish-pull-request": (
        "agentic_devtools.cli.azure_devops",
        "publish_pull_request_async",
    ),
    "agdt-run-e2e-tests-synapse": (
        "agentic_devtools.cli.azure_devops",
        "run_e2e_tests_synapse_async",
    ),
    "agdt-run-e2e-tests-fabric": (
        "agentic_devtools.cli.azure_devops",
        "run_e2e_tests_fabric_async",
    ),
    "agdt-run-wb-patch": (
        "agentic_devtools.cli.azure_devops",
        "run_wb_patch_async",
    ),
    "agdt-get-run-details": (
        "agentic_devtools.cli.azure_devops",
        "get_run_details_async",
    ),
    "agdt-wait-for-run": (
        "agentic_devtools.cli.azure_devops",
        "wait_for_run_async",
    ),
    "agdt-list-pipelines": (
        "agentic_devtools.cli.azure_devops",
        "list_pipelines_async",
    ),
    "agdt-get-pipeline-id": (
        "agentic_devtools.cli.azure_devops",
        "get_pipeline_id_async",
    ),
    "agdt-create-pipeline": (
        "agentic_devtools.cli.azure_devops",
        "create_pipeline_async",
    ),
    "agdt-update-pipeline": (
        "agentic_devtools.cli.azure_devops",
        "update_pipeline_async",
    ),
    "agdt-get-pull-request-details": (
        "agentic_devtools.cli.azure_devops",
        "get_pull_request_details_async",
    ),
    "agdt-approve-file": (
        "agentic_devtools.cli.azure_devops",
        "approve_file_async_cli",
    ),
    "agdt-submit-file-review": (
        "agentic_devtools.cli.azure_devops",
        "submit_file_review_async",
    ),
    "agdt-request-changes": (
        "agentic_devtools.cli.azure_devops",
        "request_changes_async_cli",
    ),
    "agdt-request-changes-with-suggestion": (
        "agentic_devtools.cli.azure_devops",
        "request_changes_with_suggestion_async_cli",
    ),
    "agdt-mark-file-reviewed": (
        "agentic_devtools.cli.azure_devops",
        "mark_file_reviewed_async",
    ),
    "agdt-generate-pr-summary": (
        "agentic_devtools.cli.azure_devops",
        "generate_pr_summary_async",
    ),
    # Azure CLI (App Insights queries)
    "agdt-query-app-insights": (
        "agentic_devtools.cli.azure",
        "query_app_insights_async",
    ),
    "agdt-query-fabric-dap-errors": (
        "agentic_devtools.cli.azure",
        "query_fabric_dap_errors_async",
    ),
    "agdt-query-fabric-dap-provisioning": (
        "agentic_devtools.cli.azure",
        "query_fabric_dap_provisioning_async",
    ),
    "agdt-query-fabric-dap-timeline": (
        "agentic_devtools.cli.azure",
        "query_fabric_dap_timeline_async",
    ),
    # VPN Toggle (all run in background)
    "agdt-vpn-off": (
        "agentic_devtools.cli.azure_devops.vpn_toggle",
        "vpn_off_async",
    ),
    "agdt-vpn-on": (
        "agentic_devtools.cli.azure_devops.vpn_toggle",
        "vpn_on_async",
    ),
    "agdt-vpn-status": (
        "agentic_devtools.cli.azure_devops.vpn_toggle",
        "vpn_status_async",
    ),
    # Jira
    "agdt-create-epic": ("agentic_devtools.cli.jira", "create_epic_async"),
    "agdt-create-issue": ("agentic_devtools.cli.jira", "create_issue_async"),
    "agdt-create-subtask": ("agentic_devtools.cli.jira", "create_subtask_async"),
    "agdt-add-jira-comment": ("agentic_devtools.cli.jira", "add_comment_async_cli"),
    "agdt-get-jira-issue": ("agentic_devtools.cli.jira", "get_issue_async"),
    "agdt-update-jira-issue": ("agentic_devtools.cli.jira", "update_issue_async"),
    "agdt-list-project-roles": (
        "agentic_devtools.cli.jira",
        "list_project_roles_async",
    ),
    "agdt-get-project-role-details": (
        "agentic_devtools.cli.jira",
        "get_project_role_details_async",
    ),
    "agdt-add-users-to-project-role": (
        "agentic_devtools.cli.jira",
        "add_users_to_project_role_async",
    ),
    "agdt-add-users-to-project-role-batch": (
        "agentic_devtools.cli.jira",
        "add_users_to_project_role_batch_async",
    ),
    "agdt-find-role-id-by-name": (
        "agentic_devtools.cli.jira",
        "find_role_id_by_name_async",
    ),
    "agdt-check-user-exists": (
        "agentic_devtools.cli.jira",
        "check_user_exists_async",
    ),
    "agdt-check-users-exist": (
        "agentic_devtools.cli.jira",
        "check_users_exist_async",
    ),
    "agdt-parse-jira-error-report": (
        "agentic_devtools.cli.jira",
        "parse_jira_error_report",
    ),
    # Git
    "agdt-git-save-work": ("agentic_devtools.cli.git", "commit_async"),
    "agdt-git-sync": ("agentic_devtools.cli.git", "sync_async"),
    "agdt-git-stage": ("agentic_devtools.cli.git", "stage_async"),
    "agdt-git-push": ("agentic_devtools.cli.git", "push_async"),
    "agdt-git-force-push": ("agentic_devtools.cli.git", "force_push_async"),
    "agdt-git-publish": ("agentic_devtools.cli.git", "publish_async"),
    # Testing
    "agdt-test": ("agentic_devtools.cli.testing", "run_tests"),
    "agdt-test-quick": ("agentic_devtools.cli.testing", "run_tests_quick"),
    "agdt-test-file": ("agentic_devtools.cli.testing", "run_tests_file"),
    "agdt-test-pattern": ("agentic_devtools.cli.testing", "run_tests_pattern"),
    # Tasks
    "agdt-tasks": ("agentic_devtools.cli.tasks", "list_tasks"),
    "agdt-task-status": ("agentic_devtools.cli.tasks", "task_status"),
    "agdt-task-log": ("agentic_devtools.cli.tasks", "task_log"),
    "agdt-task-wait": ("agentic_devtools.cli.tasks", "task_wait"),
    "agdt-tasks-clean": ("agentic_devtools.cli.tasks", "tasks_clean"),
    "agdt-show-other-incomplete-tasks": (
        "agentic_devtools.cli.tasks",
        "show_other_incomplete_tasks",
    ),
    # Workflows
    "agdt-initiate-pull-request-review-workflow": (
        "agentic_devtools.cli.workflows",
        "initiate_pull_request_review_workflow",
    ),
    "agdt-initiate-work-on-jira-issue-workflow": (
        "agentic_devtools.cli.workflows",
        "initiate_work_on_jira_issue_workflow",
    ),
    "agdt-initiate-create-jira-issue-workflow": (
        "agentic_devtools.cli.workflows",
        "initiate_create_jira_issue_workflow",
    ),
    "agdt-initiate-create-jira-epic-workflow": (
        "agentic_devtools.cli.workflows",
        "initiate_create_jira_epic_workflow",
    ),
    "agdt-initiate-create-jira-subtask-workflow": (
        "agentic_devtools.cli.workflows",
        "initiate_create_jira_subtask_workflow",
    ),
    "agdt-initiate-update-jira-issue-workflow": (
        "agentic_devtools.cli.workflows",
        "initiate_update_jira_issue_workflow",
    ),
    "agdt-initiate-apply-pr-suggestions-workflow": (
        "agentic_devtools.cli.workflows",
        "initiate_apply_pull_request_review_suggestions_workflow",
    ),
    "agdt-advance-workflow": (
        "agentic_devtools.cli.workflows",
        "advance_workflow_cmd",
    ),
    "agdt-get-next-workflow-prompt": (
        "agentic_devtools.cli.workflows",
        "get_next_workflow_prompt_cmd",
    ),
    "agdt-create-checklist": (
        "agentic_devtools.cli.workflows",
        "create_checklist_cmd",
    ),
    "agdt-update-checklist": (
        "agentic_devtools.cli.workflows",
        "update_checklist_cmd",
    ),
    "agdt-show-checklist": (
        "agentic_devtools.cli.workflows",
        "show_checklist_cmd",
    ),
    # Background worktree setup (internal, called by background task)
    "agdt-setup-worktree-background": (
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
        print("Example: python -m agentic_devtools.cli.runner agdt-set key value")
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
