"""
Workflow commands package.

Provides CLI commands for initiating and managing workflows with overrideable prompts.
"""

import sys

from .commands import (
    advance_pull_request_review_workflow,
    advance_work_on_jira_issue_workflow,
    create_checklist_cmd,
    initiate_apply_pull_request_review_suggestions_workflow,
    initiate_create_jira_epic_workflow,
    initiate_create_jira_issue_workflow,
    initiate_create_jira_subtask_workflow,
    initiate_pull_request_review_workflow,
    initiate_update_jira_issue_workflow,
    initiate_work_on_jira_issue_workflow,
    setup_worktree_background_cmd,
    show_checklist_cmd,
    update_checklist_cmd,
)
from .manager import (
    NotifyEventResult,
    WorkflowEvent,
    get_next_workflow_prompt,
    get_next_workflow_prompt_cmd,
    notify_workflow_event,
)


def advance_workflow_cmd() -> None:
    """
    CLI entry point for advancing a workflow to the next step.

    Usage: agdt-advance-workflow [step]

    If step is not provided, advances to the next step automatically.
    """
    step = sys.argv[1] if len(sys.argv) > 1 else None

    # Currently only work-on-jira-issue supports manual advancement
    # Future: Check which workflow is active and call appropriate advance function
    from ...state import get_workflow_state

    workflow = get_workflow_state()
    if not workflow:
        print("ERROR: No workflow is currently active.", file=sys.stderr)
        sys.exit(1)

    workflow_name = workflow.get("active", "")
    if workflow_name == "work-on-jira-issue":
        advance_work_on_jira_issue_workflow(step)
    elif workflow_name == "pull-request-review":
        advance_pull_request_review_workflow(step)
    else:
        print(f"ERROR: Workflow '{workflow_name}' does not support manual advancement.", file=sys.stderr)
        sys.exit(1)


__all__ = [
    "initiate_pull_request_review_workflow",
    "initiate_work_on_jira_issue_workflow",
    "initiate_create_jira_issue_workflow",
    "initiate_create_jira_epic_workflow",
    "initiate_create_jira_subtask_workflow",
    "initiate_update_jira_issue_workflow",
    "initiate_apply_pull_request_review_suggestions_workflow",
    "setup_worktree_background_cmd",
    "advance_workflow_cmd",
    "get_next_workflow_prompt",
    "get_next_workflow_prompt_cmd",
    "notify_workflow_event",
    "NotifyEventResult",
    "WorkflowEvent",
    "create_checklist_cmd",
    "update_checklist_cmd",
    "show_checklist_cmd",
]
