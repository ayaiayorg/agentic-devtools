"""
Azure DevOps CLI utilities package.

This package provides command-line tools for interacting with Azure DevOps,
including pull request management, thread handling, and approvals.

Workflow:
    1. Set state values with dfly-set (auto-approve once)
    2. Execute action with dfly-<action> (auto-approve once)

Example:
    agdt-set pull_request_id 23046
    agdt-set thread_id 139474
    agdt-set content "Thanks for the feedback!

    I've made the changes you suggested."
    agdt-reply-to-pull-request-thread
"""

# Config exports
# Auth exports
# Async command exports
from .async_commands import (
    add_pull_request_comment_async,
    approve_file_async,
    approve_file_async_cli,
    approve_pull_request_async,
    create_pipeline_async,
    create_pull_request_async,
    create_pull_request_async_cli,
    generate_pr_summary_async,
    get_pipeline_id_async,
    get_pull_request_details_async,
    get_pull_request_threads_async,
    get_run_details_async,
    list_pipelines_async,
    mark_file_reviewed_async,
    mark_pull_request_draft_async,
    publish_pull_request_async,
    reply_to_pull_request_thread_async,
    request_changes_async,
    request_changes_async_cli,
    request_changes_with_suggestion_async,
    request_changes_with_suggestion_async_cli,
    resolve_thread_async,
    run_e2e_tests_fabric_async,
    run_e2e_tests_synapse_async,
    run_wb_patch_async,
    submit_file_review_async,
    update_pipeline_async,
    wait_for_run_async,
)
from .auth import get_auth_headers, get_pat

# Command exports
from .commands import (
    add_pull_request_comment,
    approve_pull_request,
    create_pull_request,
    get_pull_request_threads,
    mark_pull_request_draft,
    parse_bool_from_state,
    publish_pull_request,
    reply_to_pull_request_thread,
    require_content,
    resolve_thread,
)
from .config import (
    API_VERSION,
    APPROVAL_SENTINEL,
    DEFAULT_ORGANIZATION,
    DEFAULT_PROJECT,
    DEFAULT_REPOSITORY,
    AzureDevOpsConfig,
)

# File review command exports
from .file_review_commands import (
    approve_file,
    get_queue_status,
    request_changes,
    request_changes_with_suggestion,
    submit_file_review,
)

# Helper exports
from .helpers import (
    build_thread_context,
    convert_to_pull_request_title,
    find_pull_request_by_issue_key,
    format_approval_content,
    get_pull_request_source_branch,
    get_repository_id,
    parse_bool_from_state_value,
    parse_json_response,
    print_threads,
    require_requests,
    resolve_thread_by_id,
    verify_az_cli,
)

# Mark reviewed export
from .mark_reviewed import mark_file_reviewed, mark_file_reviewed_cli

# Pipeline command exports
from .pipeline_commands import (
    create_pipeline,
    get_pipeline_id,
    list_pipelines,
    run_e2e_tests_fabric,
    run_e2e_tests_synapse,
    run_wb_patch,
    update_pipeline,
)

# PR summary command exports
from .pr_summary_commands import (
    generate_overarching_pr_comments,
    generate_overarching_pr_comments_cli,
)

# Pull request details command exports
from .pull_request_details_commands import get_pull_request_details

# Run details command exports
from .run_details_commands import get_run_details, wait_for_run

__all__ = [
    # Constants
    "DEFAULT_ORGANIZATION",
    "DEFAULT_PROJECT",
    "DEFAULT_REPOSITORY",
    "APPROVAL_SENTINEL",
    "API_VERSION",
    # Config
    "AzureDevOpsConfig",
    # Auth
    "get_pat",
    "get_auth_headers",
    # Helpers
    "parse_bool_from_state_value",
    "require_requests",
    "get_repository_id",
    "resolve_thread_by_id",
    "convert_to_pull_request_title",
    "format_approval_content",
    "build_thread_context",
    "verify_az_cli",
    "parse_json_response",
    "print_threads",
    "find_pull_request_by_issue_key",
    "get_pull_request_source_branch",
    # Command helpers
    "parse_bool_from_state",
    "require_content",
    # Commands (sync)
    "reply_to_pull_request_thread",
    "add_pull_request_comment",
    "create_pull_request",
    "resolve_thread",
    "get_pull_request_threads",
    "approve_pull_request",
    "mark_pull_request_draft",
    "publish_pull_request",
    # Commands (async)
    "add_pull_request_comment_async",
    "approve_pull_request_async",
    "create_pull_request_async",
    "create_pull_request_async_cli",
    "get_pull_request_threads_async",
    "reply_to_pull_request_thread_async",
    "resolve_thread_async",
    "mark_pull_request_draft_async",
    "publish_pull_request_async",
    "get_pull_request_details_async",
    # Pipeline commands
    "run_e2e_tests_fabric",
    "run_e2e_tests_synapse",
    "run_wb_patch",
    "list_pipelines",
    "get_pipeline_id",
    "create_pipeline",
    "update_pipeline",
    # Pipeline commands (async)
    "run_e2e_tests_fabric_async",
    "run_e2e_tests_synapse_async",
    "run_wb_patch_async",
    "get_run_details_async",
    "list_pipelines_async",
    "get_pipeline_id_async",
    "create_pipeline_async",
    "update_pipeline_async",
    # Pull request details command
    "get_pull_request_details",
    # File review commands
    "approve_file",
    "get_queue_status",
    "submit_file_review",
    "request_changes",
    "request_changes_with_suggestion",
    # File review commands (async)
    "approve_file_async",
    "approve_file_async_cli",
    "submit_file_review_async",
    "request_changes_async",
    "request_changes_async_cli",
    "request_changes_with_suggestion_async",
    "request_changes_with_suggestion_async_cli",
    "mark_file_reviewed_async",
    # Mark reviewed
    "mark_file_reviewed",
    "mark_file_reviewed_cli",
    # PR summary commands
    "generate_overarching_pr_comments",
    "generate_overarching_pr_comments_cli",
    # PR summary commands (async)
    "generate_pr_summary_async",
    # Run details commands
    "get_run_details",
    "wait_for_run",
    "wait_for_run_async",
]
