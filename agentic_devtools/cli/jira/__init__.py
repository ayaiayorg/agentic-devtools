"""
Jira CLI module for agentic-devtools.

This package provides CLI commands for interacting with Jira:
- create_epic: Create a Jira Epic
- create_issue: Create a Jira issue (Task, Story, Bug, etc.)
- create_subtask: Create a Sub-task under a parent issue
- add_comment: Add a comment to an issue
    # Async status
    "write_async_status",
    # Commands
    "add_comment",
    "create_epic",
    "create_issue",
    "create_issue_sync",
    "create_subtask",
    "get_issue",
    "update_issue",
    # Async command wrappers
    "add_comment_async",
    "add_comment_async_cli",
    "add_users_to_project_role_async",
    "add_users_to_project_role_batch_async",
    "check_user_exists_async",
    "check_users_exist_async",
    "create_epic_async",
    "create_issue_async",
    "create_subtask_async",
    "find_role_id_by_name_async",
    "get_issue_async",
    "get_project_role_details_async",
    "list_project_roles_async",
    "update_issue_async",
)

# Async command wrappers
from .async_commands import (
    add_comment_async,
    add_comment_async_cli,
    "check_user_exists",
    "check_users_exist",
    "find_role_id_by_name",
    "get_project_role_details",
    "list_project_roles",
)

# Async status
from .async_status import write_async_status

# CLI commands
from .commands import (
    add_comment,
    create_epic,
    create_issue,
    create_issue_sync,
    create_subtask,
    get_issue,
)
from .config import (
    DEFAULT_JIRA_BASE_URL,
    DEFAULT_PROJECT_KEY,
    EPIC_NAME_FIELD,
    get_jira_auth_header,
    get_jira_base_url,
    get_jira_headers,
)

# Formatting utilities
from .formatting import (
    build_user_story_description,
    format_bullet_list,
    merge_labels,
)

# Helper utilities
from .helpers import (
    _get_requests,
    _get_ssl_verify,
    _parse_comma_separated,
    _parse_multiline_string,
)

# Error report parsing
from .parse_error_report import parse_jira_error_report

# Role management commands
from .role_commands import (
    add_users_to_project_role,
    add_users_to_project_role_batch,
    check_user_exists,
    check_users_exist,
    find_role_id_by_name,
    get_project_role_details,
    list_project_roles,
)

# State namespace helpers
from .state_helpers import (
    JIRA_STATE_NAMESPACE,
    get_jira_value,
    set_jira_value,
)

# Update commands
from .update_commands import update_issue

__all__ = [
    # Constants
    "DEFAULT_JIRA_BASE_URL",
    "DEFAULT_PROJECT_KEY",
    "EPIC_NAME_FIELD",
    "JIRA_STATE_NAMESPACE",
    # Config functions
    "get_jira_auth_header",
    "get_jira_base_url",
    "get_jira_headers",
    # Helpers
    "_get_requests",
    "_get_ssl_verify",
    "_parse_comma_separated",
    "_parse_multiline_string",
    # State helpers
    "get_jira_value",
    "set_jira_value",
    # Formatting
    "build_user_story_description",
    "format_bullet_list",
    "merge_labels",
    # ADF
    "_convert_adf_to_text",
    "_process_adf_children",
    # Async status
    "write_async_status",
    # Commands
    "add_comment",
    "create_epic",
    "create_issue",
    "create_issue_sync",
    "create_subtask",
    "get_issue",
    "update_issue",
    # Async command wrappers
    "add_comment_async",
    "add_comment_async_cli",
    "add_users_to_project_role_async",
    "add_users_to_project_role_batch_async",
    "check_user_exists_async",
    "check_users_exist_async",
    "create_epic_async",
    "create_issue_async",
    "create_subtask_async",
    "find_role_id_by_name_async",
    "get_issue_async",
    "get_project_role_details_async",
    "list_project_roles_async",
    "update_issue_async",
    # Error report parsing
    "parse_jira_error_report",
    # Role management commands
    "add_users_to_project_role",
    "add_users_to_project_role_batch",
    "check_user_exists",
    "check_users_exist",
    "find_role_id_by_name",
    "get_project_role_details",
    "list_project_roles",
]
