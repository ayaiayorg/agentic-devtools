"""Standalone tool adapter functions for Jira, Git, and Azure DevOps.

Each function accepts typed parameters and returns structured TypedDict results,
suitable for use as LangGraph graph nodes, MCP tools, or direct programmatic APIs.

Usage::

    from agentic_devtools.tools import jira, git, azure_devops
    from agentic_devtools.tools.jira import create_issue, JiraConfig
"""

from .azure_devops import (
    add_pull_request_comment,
    add_reviewer,
    complete_pull_request,
    create_pull_request,
    file_review,
    reply_to_pull_request_thread,
    update_review_narrative,
)
from .git import (
    amend_commit,
    create_commit,
    force_push,
    get_recent_changes,
    publish_branch,
    push,
    save_work,
    stage_changes,
)
from .jira import (
    add_comment,
    create_epic,
    create_issue,
    create_subtask,
    fetch_issue_context,
)

__all__ = [
    # Jira
    "add_comment",
    "create_epic",
    "create_issue",
    "create_subtask",
    "fetch_issue_context",
    # Git
    "amend_commit",
    "create_commit",
    "force_push",
    "get_recent_changes",
    "publish_branch",
    "push",
    "save_work",
    "stage_changes",
    # Azure DevOps
    "add_pull_request_comment",
    "add_reviewer",
    "complete_pull_request",
    "create_pull_request",
    "file_review",
    "reply_to_pull_request_thread",
    "update_review_narrative",
]
