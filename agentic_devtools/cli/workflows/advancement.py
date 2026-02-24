"""
Workflow advancement helpers.

This module provides functions that can be called by other commands
to automatically notify the workflow manager of events and trigger transitions.

All advancement is now event-driven through notify_workflow_event().
"""

from typing import Any, Dict, Optional

from .manager import WorkflowEvent, notify_workflow_event


def try_advance_workflow_after_jira_comment(task_id: Optional[str] = None) -> bool:
    """
    Notify the workflow manager that a Jira comment was added.

    This may trigger a transition from 'planning' to 'implementation'.

    Args:
        task_id: Optional background task ID that completed

    Returns:
        True if a workflow transition was triggered, False otherwise
    """
    result = notify_workflow_event(
        event=WorkflowEvent.JIRA_COMMENT_ADDED,
        task_id=task_id,
    )

    if result.triggered and not result.immediate_advance:  # pragma: no cover
        print("\n[Workflow] Event recorded: Jira comment added.")
        print("Run 'agdt-get-next-workflow-prompt' to continue.")

    return result.triggered


def try_advance_workflow_after_jira_issue_retrieved(
    task_id: Optional[str] = None,
    issue_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Notify the workflow manager that Jira issue details were retrieved.

    This may trigger a transition from 'initiate' to 'planning'.

    Args:
        task_id: Optional background task ID that completed
        issue_data: Optional issue data to store in context

    Returns:
        True if a workflow transition was triggered, False otherwise
    """
    context_updates = {}
    if issue_data:
        fields = issue_data.get("fields", {})
        context_updates.update(
            {
                "issue_summary": fields.get("summary", ""),
                "issue_type": fields.get("issuetype", {}).get("name", ""),
                "issue_labels": ", ".join(fields.get("labels", [])),
                "issue_description": fields.get("description", ""),
            }
        )

    result = notify_workflow_event(
        event=WorkflowEvent.JIRA_ISSUE_RETRIEVED,
        task_id=task_id,
        context_updates=context_updates,
    )

    if result.triggered and not result.immediate_advance:
        print("\n[Workflow] Event recorded: Jira issue retrieved.")
        print("Run 'agdt-get-next-workflow-prompt' to continue.")

    return result.triggered


def try_advance_workflow_after_commit(
    task_id: Optional[str] = None,
    branch_name: Optional[str] = None,
) -> bool:
    """
    Notify the workflow manager that a git commit was created.

    This may trigger a transition from 'commit' to 'pull-request'.

    Args:
        task_id: Optional background task ID that completed
        branch_name: The branch name (for context, optional)

    Returns:
        True if a workflow transition was triggered, False otherwise
    """
    context_updates = {}
    if branch_name:
        context_updates["branch_name"] = branch_name

    result = notify_workflow_event(
        event=WorkflowEvent.GIT_COMMIT_CREATED,
        task_id=task_id,
        context_updates=context_updates,
    )

    if result.triggered and not result.immediate_advance:
        print("\n[Workflow] Event recorded: Git commit created.")
        print("Run 'agdt-get-next-workflow-prompt' to continue.")

    return result.triggered


def try_advance_workflow_after_branch_pushed(
    task_id: Optional[str] = None,
    branch_name: Optional[str] = None,
) -> bool:
    """
    Notify the workflow manager that a branch was pushed.

    This may also trigger a transition from 'commit' to 'pull-request'.

    Args:
        task_id: Optional background task ID that completed
        branch_name: The branch name (for context, optional)

    Returns:
        True if a workflow transition was triggered, False otherwise
    """
    context_updates = {}
    if branch_name:
        context_updates["branch_name"] = branch_name

    result = notify_workflow_event(
        event=WorkflowEvent.GIT_BRANCH_PUSHED,
        task_id=task_id,
        context_updates=context_updates,
    )

    if result.triggered and not result.immediate_advance:
        print("\n[Workflow] Event recorded: Branch pushed.")
        print("Run 'agdt-get-next-workflow-prompt' to continue.")

    return result.triggered


def try_advance_workflow_after_pr_creation(
    pull_request_id: Optional[int] = None,
    pull_request_url: Optional[str] = None,
    task_id: Optional[str] = None,
) -> bool:
    """
    Notify the workflow manager that a PR was created.

    This may trigger a transition from 'pull-request' to 'completion'.

    Args:
        pull_request_id: The created PR ID
        pull_request_url: The PR URL (optional)
        task_id: Optional background task ID that completed

    Returns:
        True if a workflow transition was triggered, False otherwise
    """
    context_updates = {}
    if pull_request_id:
        context_updates["pull_request_id"] = pull_request_id
    if pull_request_url:
        context_updates["pull_request_url"] = pull_request_url

    result = notify_workflow_event(
        event=WorkflowEvent.PR_CREATED,
        task_id=task_id,
        context_updates=context_updates,
    )

    if result.triggered and not result.immediate_advance:
        print("\n[Workflow] Event recorded: Pull request created.")
        print("Run 'agdt-get-next-workflow-prompt' to continue.")

    return result.triggered


def try_advance_workflow_after_pr_review(
    task_id: Optional[str] = None,
) -> bool:
    """
    Notify the workflow manager that a PR was reviewed.

    Args:
        task_id: Optional background task ID that completed

    Returns:
        True if a workflow transition was triggered, False otherwise
    """
    result = notify_workflow_event(
        event=WorkflowEvent.PR_REVIEWED,
        task_id=task_id,
    )

    if result.triggered and not result.immediate_advance:  # pragma: no cover
        print("\n[Workflow] Event recorded: Pull request reviewed.")
        print("Run 'agdt-get-next-workflow-prompt' to continue.")

    return result.triggered
