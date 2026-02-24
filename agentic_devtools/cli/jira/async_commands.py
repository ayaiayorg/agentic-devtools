"""
Async Jira command wrappers.

Provides async versions of Jira commands that run in background processes.
All commands that make HTTP requests to Jira should have async versions here.

These async commands call the sync functions directly via run_function_in_background,
not via CLI entry points.
"""

import argparse
import sys
from typing import Optional

from agentic_devtools.background_tasks import run_function_in_background
from agentic_devtools.state import set_value
from agentic_devtools.task_state import print_task_tracking_info

from .state_helpers import get_jira_value


def _require_jira_value(key: str, error_example: str) -> str:
    """Get a required Jira state value or exit with error."""
    value = get_jira_value(key)
    if not value:
        print(
            f"Error: jira.{key} is required. Use: {error_example}",
            file=sys.stderr,
        )
        sys.exit(1)
    return value


def _set_jira_value_if_provided(key: str, value: Optional[str]) -> None:
    """Set a Jira state value if provided (not None)."""
    if value is not None:
        set_value(f"jira.{key}", value)


# Module paths for the sync functions
_COMMENT_MODULE = "agentic_devtools.cli.jira.comment_commands"
_CREATE_MODULE = "agentic_devtools.cli.jira.create_commands"
_GET_MODULE = "agentic_devtools.cli.jira.get_commands"
_UPDATE_MODULE = "agentic_devtools.cli.jira.update_commands"
_ROLE_MODULE = "agentic_devtools.cli.jira.role_commands"


# =============================================================================
# Comment Commands (Async)
# =============================================================================


def add_comment_async(
    comment: Optional[str] = None,
    issue_key: Optional[str] = None,
) -> None:
    """
    Add a Jira comment asynchronously in the background.

    This command immediately returns after spawning a background task.
    Use agdt-task-status or agdt-task-wait to check completion.

    Args:
        comment: Comment content (overrides state)
        issue_key: Issue key to comment on (overrides state)

    State keys (prefixed with 'jira.'):
    - jira.issue_key: Issue key (used if issue_key not provided)
    - jira.comment: Comment content (used if comment not provided)

    Outputs:
    - Prints task ID for tracking

    Usage:
        agdt-add-jira-comment --jira-comment "This is my comment"
        agdt-add-jira-comment --jira-issue-key DFLY-1234 --jira-comment "Comment"

        # Or using state:
        agdt-set jira.issue_key DFLY-1234
        agdt-set jira.comment "This is my comment"
        agdt-add-jira-comment
        # Returns immediately with task ID
    """
    # Store CLI args in state if provided (background task reads from state)
    _set_jira_value_if_provided("issue_key", issue_key)
    _set_jira_value_if_provided("comment", comment)

    # Validate required values exist in state
    resolved_issue_key = _require_jira_value("issue_key", "agdt-add-jira-comment --jira-issue-key DFLY-1234")
    _require_jira_value("comment", 'agdt-add-jira-comment --jira-comment "Your comment"')

    task = run_function_in_background(
        _COMMENT_MODULE,
        "add_comment",
        command_display_name="agdt-add-jira-comment",
    )
    print_task_tracking_info(task, f"Adding comment to {resolved_issue_key}")


def add_comment_async_cli() -> None:  # pragma: no cover
    """CLI entry point for add_comment_async with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Add a comment to a Jira issue (async)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agdt-add-jira-comment --jira-comment "This is my comment"
  agdt-add-jira-comment --jira-issue-key DFLY-1234 --jira-comment "Comment"

  # Or using state:
  agdt-set jira.issue_key DFLY-1234
  agdt-set jira.comment "This is my comment"
  agdt-add-jira-comment
        """,
    )

    parser.add_argument(
        "--jira-comment",
        "-c",
        type=str,
        default=None,
        help="Comment content to add (falls back to jira.comment state)",
    )
    parser.add_argument(
        "--jira-issue-key",
        "-k",
        type=str,
        default=None,
        help="Issue key to comment on (falls back to jira.issue_key state)",
    )

    args = parser.parse_args()

    add_comment_async(comment=args.jira_comment, issue_key=args.jira_issue_key)


# =============================================================================
# Issue CRUD Commands (Async)
# =============================================================================


def create_epic_async() -> None:
    """
    Create a Jira epic asynchronously in the background.

    Reads from state (all keys prefixed with 'jira.'):
    - jira.project_key (required): Project key (e.g., 'DFLY')
    - jira.summary (required): Epic summary/title
    - jira.epic_name (required): Epic name field
    - jira.role (optional): User story role
    - jira.desired_outcome (optional): User story desired outcome
    - jira.benefit (optional): User story benefit
    - jira.description (optional): Additional description
    - jira.labels (optional): Comma-separated labels

    Usage:
        agdt-set jira.project_key DFLY
        agdt-set jira.summary "New Feature Epic"
        agdt-set jira.epic_name "Feature Epic"
        agdt-create-epic
    """
    _require_jira_value("project_key", "agdt-set jira.project_key DFLY")
    _require_jira_value("summary", 'agdt-set jira.summary "Epic Title"')
    _require_jira_value("epic_name", 'agdt-set jira.epic_name "Epic Name"')

    task = run_function_in_background(
        _CREATE_MODULE,
        "create_epic",
        command_display_name="agdt-create-epic",
    )
    print_task_tracking_info(task, "Creating epic")


def create_issue_async() -> None:
    """
    Create a Jira issue asynchronously in the background.

    Reads from state (all keys prefixed with 'jira.'):
    - jira.project_key (required): Project key (e.g., 'DFLY')
    - jira.summary (required): Issue summary/title
    - jira.description (optional): Issue description
    - jira.issue_type (optional): Issue type (default: 'Task')
    - jira.labels (optional): Comma-separated labels
    - jira.parent_key (optional): Parent epic key

    Usage:
        agdt-set jira.project_key DFLY
        agdt-set jira.summary "New Task"
        agdt-set jira.description "Task description"
        agdt-create-issue
    """
    _require_jira_value("project_key", "agdt-set jira.project_key DFLY")
    _require_jira_value("summary", 'agdt-set jira.summary "Issue Title"')

    task = run_function_in_background(
        _CREATE_MODULE,
        "create_issue",
        command_display_name="agdt-create-issue",
    )
    print_task_tracking_info(task, "Creating issue")


def create_subtask_async() -> None:
    """
    Create a Jira subtask asynchronously in the background.

    Reads from state (all keys prefixed with 'jira.'):
    - jira.parent_key (required): Parent issue key
    - jira.summary (required): Subtask summary/title
    - jira.description (optional): Subtask description

    Usage:
        agdt-set jira.parent_key DFLY-1234
        agdt-set jira.summary "Subtask Title"
        agdt-create-subtask
    """
    parent_key = _require_jira_value("parent_key", "agdt-set jira.parent_key DFLY-1234")
    _require_jira_value("summary", 'agdt-set jira.summary "Subtask Title"')

    task = run_function_in_background(
        _CREATE_MODULE,
        "create_subtask",
        command_display_name="agdt-create-subtask",
    )
    print_task_tracking_info(task, f"Creating subtask under {parent_key}")


def get_issue_async() -> None:
    """
    Get Jira issue details asynchronously in the background.

    Reads from state (all keys prefixed with 'jira.'):
    - jira.issue_key (required): Issue key to retrieve

    Usage:
        agdt-set jira.issue_key DFLY-1234
        agdt-get-jira-issue
    """
    issue_key = _require_jira_value("issue_key", "agdt-set jira.issue_key DFLY-1234")

    task = run_function_in_background(
        _GET_MODULE,
        "get_issue",
        command_display_name="agdt-get-jira-issue",
    )
    print_task_tracking_info(task, f"Getting issue {issue_key}")


def update_issue_async() -> None:
    """
    Update a Jira issue asynchronously in the background.

    Reads from state (all keys prefixed with 'jira.'):
    - jira.issue_key (required): Issue key to update
    - Plus any update fields (jira.summary, jira.description, etc.)

    Usage:
        agdt-set jira.issue_key DFLY-1234
        agdt-set jira.summary "New Summary"
        agdt-update-jira-issue
    """
    issue_key = _require_jira_value("issue_key", "agdt-set jira.issue_key DFLY-1234")

    task = run_function_in_background(
        _UPDATE_MODULE,
        "update_issue",
        command_display_name="agdt-update-jira-issue",
    )
    print_task_tracking_info(task, f"Updating {issue_key}")


# =============================================================================
# Role Management Commands (Async)
# =============================================================================


def list_project_roles_async() -> None:
    """
    List project roles asynchronously in the background.

    Reads from state (all keys prefixed with 'jira.'):
    - jira.project_key (required): Project key

    Usage:
        agdt-set jira.project_key DFLY
        agdt-list-project-roles
    """
    project_key = _require_jira_value("project_key", "agdt-set jira.project_key DFLY")

    task = run_function_in_background(
        _ROLE_MODULE,
        "list_project_roles",
        command_display_name="agdt-list-project-roles",
    )
    print_task_tracking_info(task, f"Listing roles for project {project_key}")


def get_project_role_details_async() -> None:
    """
    Get project role details asynchronously in the background.

    Reads from state (all keys prefixed with 'jira.'):
    - jira.project_key (required): Project key
    - jira.role_id (required): Role ID

    Usage:
        agdt-set jira.project_key DFLY
        agdt-set jira.role_id 10002
        agdt-get-project-role-details
    """
    project_key = _require_jira_value("project_key", "agdt-set jira.project_key DFLY")
    _require_jira_value("role_id", "agdt-set jira.role_id 10002")

    task = run_function_in_background(
        _ROLE_MODULE,
        "get_project_role_details",
        command_display_name="agdt-get-project-role-details",
    )
    print_task_tracking_info(task, f"Getting role details for project {project_key}")


def add_users_to_project_role_async() -> None:
    """
    Add users to a project role asynchronously in the background.

    Reads from state (all keys prefixed with 'jira.'):
    - jira.project_key (required): Project key
    - jira.role_id (required): Role ID
    - jira.users (required): Comma-separated list of usernames

    Usage:
        agdt-set jira.project_key DFLY
        agdt-set jira.role_id 10002
        agdt-set jira.users "user1,user2"
        agdt-add-users-to-project-role
    """
    project_key = _require_jira_value("project_key", "agdt-set jira.project_key DFLY")
    _require_jira_value("role_id", "agdt-set jira.role_id 10002")
    _require_jira_value("users", 'agdt-set jira.users "user1,user2"')

    task = run_function_in_background(
        _ROLE_MODULE,
        "add_users_to_project_role",
        command_display_name="agdt-add-users-to-project-role",
    )
    print_task_tracking_info(task, f"Adding users to role in project {project_key}")


def add_users_to_project_role_batch_async() -> None:
    """
    Add users to a project role in batch asynchronously.

    Reads from state (all keys prefixed with 'jira.'):
    - jira.project_key (required): Project key
    - jira.role_id (required): Role ID
    - jira.users (required): Comma-separated list of usernames

    Usage:
        agdt-set jira.project_key DFLY
        agdt-set jira.role_id 10002
        agdt-set jira.users "user1,user2,user3"
        agdt-add-users-to-project-role-batch
    """
    project_key = _require_jira_value("project_key", "agdt-set jira.project_key DFLY")
    _require_jira_value("role_id", "agdt-set jira.role_id 10002")
    _require_jira_value("users", 'agdt-set jira.users "user1,user2,user3"')

    task = run_function_in_background(
        _ROLE_MODULE,
        "add_users_to_project_role_batch",
        command_display_name="agdt-add-users-to-project-role-batch",
    )
    print_task_tracking_info(task, f"Batch adding users to role in project {project_key}")


def find_role_id_by_name_async() -> None:
    """
    Find a role ID by name asynchronously in the background.

    Reads from state (all keys prefixed with 'jira.'):
    - jira.project_key (required): Project key
    - jira.role_name (required): Role name to find

    Usage:
        agdt-set jira.project_key DFLY
        agdt-set jira.role_name "Developers"
        agdt-find-role-id-by-name
    """
    project_key = _require_jira_value("project_key", "agdt-set jira.project_key DFLY")
    _require_jira_value("role_name", 'agdt-set jira.role_name "Developers"')

    task = run_function_in_background(
        _ROLE_MODULE,
        "find_role_id_by_name",
        command_display_name="agdt-find-role-id-by-name",
    )
    print_task_tracking_info(task, f"Finding role ID in project {project_key}")


def check_user_exists_async() -> None:
    """
    Check if a user exists asynchronously in the background.

    Reads from state (all keys prefixed with 'jira.'):
    - jira.username (required): Username to check

    Usage:
        agdt-set jira.username "amarsnik"
        agdt-check-user-exists
    """
    username = _require_jira_value("username", "agdt-set jira.username amarsnik")

    task = run_function_in_background(
        _ROLE_MODULE,
        "check_user_exists",
        command_display_name="agdt-check-user-exists",
    )
    print_task_tracking_info(task, f"Checking if user {username} exists")


def check_users_exist_async() -> None:
    """
    Check if multiple users exist asynchronously in the background.

    Reads from state (all keys prefixed with 'jira.'):
    - jira.users (required): Comma-separated list of usernames

    Usage:
        agdt-set jira.users "user1,user2,user3"
        agdt-check-users-exist
    """
    _require_jira_value("users", 'agdt-set jira.users "user1,user2,user3"')

    task = run_function_in_background(
        _ROLE_MODULE,
        "check_users_exist",
        command_display_name="agdt-check-users-exist",
    )
    print_task_tracking_info(task, "Checking if users exist")
