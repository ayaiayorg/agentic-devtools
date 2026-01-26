"""Jira CLI module for agentic-devtools."""

from .adf import _convert_adf_to_text, _process_adf_children
from .async_commands import (
    add_comment_async,
    add_comment_async_cli,
    add_users_to_project_role_async,
    add_users_to_project_role_batch_async,
    check_user_exists_async,
    check_users_exist_async,
    create_epic_async,
    create_issue_async,
    create_subtask_async,
    find_role_id_by_name_async,
    get_issue_async,
    get_project_role_details_async,
    list_project_roles_async,
    update_issue_async,
)
from .async_status import write_async_status
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
from .formatting import (
    build_user_story_description,
    format_bullet_list,
    merge_labels,
)
from .helpers import (
    _get_requests,
    _get_ssl_verify,
    _parse_comma_separated,
    _parse_multiline_string,
)
from .parse_error_report import parse_jira_error_report
from .role_commands import (
    add_users_to_project_role,
    add_users_to_project_role_batch,
    check_user_exists,
    check_users_exist,
    find_role_id_by_name,
    get_project_role_details,
    list_project_roles,
)
from .state_helpers import (
    JIRA_STATE_NAMESPACE,
    get_jira_value,
    set_jira_value,
)
from .update_commands import update_issue

__all__ = [
    "DEFAULT_JIRA_BASE_URL",
    "DEFAULT_PROJECT_KEY",
    "EPIC_NAME_FIELD",
    "JIRA_STATE_NAMESPACE",
    "_convert_adf_to_text",
    "_get_requests",
    "_get_ssl_verify",
    "_parse_comma_separated",
    "_parse_multiline_string",
    "_process_adf_children",
    "add_comment",
    "add_comment_async",
    "add_comment_async_cli",
    "add_users_to_project_role",
    "add_users_to_project_role_async",
    "add_users_to_project_role_batch",
    "add_users_to_project_role_batch_async",
    "build_user_story_description",
    "check_user_exists",
    "check_user_exists_async",
    "check_users_exist",
    "check_users_exist_async",
    "create_epic",
    "create_epic_async",
    "create_issue",
    "create_issue_async",
    "create_issue_sync",
    "create_subtask",
    "create_subtask_async",
    "find_role_id_by_name",
    "find_role_id_by_name_async",
    "format_bullet_list",
    "get_issue",
    "get_issue_async",
    "get_jira_auth_header",
    "get_jira_base_url",
    "get_jira_headers",
    "get_jira_value",
    "get_project_role_details",
    "get_project_role_details_async",
    "list_project_roles",
    "list_project_roles_async",
    "merge_labels",
    "parse_jira_error_report",
    "set_jira_value",
    "update_issue",
    "update_issue_async",
    "write_async_status",
]
