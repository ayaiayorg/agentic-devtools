"""
Workflow Manager - Event-driven workflow orchestration.

This module provides:
- Workflow transition definitions (what action triggers which next step)
- Event notification from commands (dfly-add-jira-comment, dfly-git-commit, etc.)
- Status checking (pending tasks, failures, success)
- Prompt delivery based on current state

Design principles:
1. Commands notify the workflow manager after successful execution
2. The workflow manager checks background task status
3. AI agent calls agdt-get-next-workflow-prompt to get next instructions
4. Three possible responses: success (next prompt), failure (error prompt), waiting (retry instructions)
"""

import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from ...prompts import get_temp_output_dir, load_and_render_prompt
from ...state import get_value, get_workflow_state, set_workflow_state
from ...task_state import TaskStatus, get_active_tasks, get_task_by_id


def _safe_print(text: str) -> None:
    """Print text safely, handling Unicode encoding errors on Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Fall back to replacing characters that cannot be encoded
        print(text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8"))


class WorkflowEvent(str, Enum):
    """Events that can trigger workflow transitions."""

    # Jira events
    JIRA_COMMENT_ADDED = "jira_comment_added"
    JIRA_ISSUE_RETRIEVED = "jira_issue_retrieved"
    JIRA_ISSUE_CREATED = "jira_issue_created"
    JIRA_ISSUE_UPDATED = "jira_issue_updated"

    # Git events
    GIT_COMMIT_CREATED = "git_commit_created"
    GIT_BRANCH_PUSHED = "git_branch_pushed"

    # PR events
    PR_CREATED = "pr_created"
    PR_APPROVED = "pr_approved"
    PR_REVIEWED = "pr_reviewed"

    # Checklist events
    CHECKLIST_CREATED = "checklist_created"
    CHECKLIST_COMPLETE = "checklist_complete"

    # Manual advancement
    MANUAL_ADVANCE = "manual_advance"

    # Environment setup
    SETUP_COMPLETE = "setup_complete"


class PromptStatus(str, Enum):
    """Status of get-next-workflow-prompt response."""

    SUCCESS = "success"  # Background tasks complete, next prompt ready
    FAILURE = "failure"  # One or more tasks failed
    WAITING = "waiting"  # Tasks still in progress
    NO_WORKFLOW = "no_workflow"  # No active workflow


@dataclass
class WorkflowTransition:
    """
    Defines a transition from one step to another.

    Attributes:
        from_step: Current step name
        to_step: Next step name
        trigger_events: Events that can trigger this transition
        required_tasks: Background task commands that must complete
        auto_advance: If True, advance automatically when tasks complete
    """

    from_step: str
    to_step: str
    trigger_events: Set[WorkflowEvent] = field(default_factory=set)
    required_tasks: List[str] = field(default_factory=list)  # Command names
    auto_advance: bool = True


@dataclass
class WorkflowDefinition:
    """
    Complete definition of a workflow's steps and transitions.

    Attributes:
        name: Workflow name (e.g., "work-on-jira-issue")
        transitions: List of valid transitions between steps
        initial_step: First step when workflow starts
    """

    name: str
    transitions: List[WorkflowTransition]
    initial_step: str = "initiate"

    def get_transition(self, from_step: str, event: WorkflowEvent) -> Optional[WorkflowTransition]:
        """Find a transition that matches the current step and event."""
        for t in self.transitions:
            if t.from_step == from_step and event in t.trigger_events:
                return t
        return None

    def get_next_step(self, current_step: str) -> Optional[str]:
        """Get the default next step from current step (for manual advancement)."""
        for t in self.transitions:
            if t.from_step == current_step and WorkflowEvent.MANUAL_ADVANCE in t.trigger_events:
                return t.to_step
        # Fallback: find any transition from current step
        for t in self.transitions:
            if t.from_step == current_step:
                return t.to_step
        return None


# =============================================================================
# Workflow Definitions
# =============================================================================

WORK_ON_JIRA_ISSUE_WORKFLOW = WorkflowDefinition(
    name="work-on-jira-issue",
    initial_step="initiate",
    transitions=[
        # Pre-flight passed: initiate -> planning (jira issue auto-fetched)
        WorkflowTransition(
            from_step="initiate",
            to_step="planning",
            trigger_events={WorkflowEvent.JIRA_ISSUE_RETRIEVED},
            required_tasks=["agdt-get-jira-issue"],
            auto_advance=True,
        ),
        # Pre-flight failed: initiate -> setup
        WorkflowTransition(
            from_step="initiate",
            to_step="setup",
            trigger_events={WorkflowEvent.SETUP_COMPLETE},
            auto_advance=True,
        ),
        # Planning complete: planning -> checklist-creation (after posting plan comment)
        WorkflowTransition(
            from_step="planning",
            to_step="checklist-creation",
            trigger_events={WorkflowEvent.JIRA_COMMENT_ADDED, WorkflowEvent.MANUAL_ADVANCE},
        ),
        # Checklist created: checklist-creation -> implementation
        WorkflowTransition(
            from_step="checklist-creation",
            to_step="implementation",
            trigger_events={WorkflowEvent.CHECKLIST_CREATED, WorkflowEvent.MANUAL_ADVANCE},
        ),
        # Implementation checklist complete: implementation -> implementation-review
        WorkflowTransition(
            from_step="implementation",
            to_step="implementation-review",
            trigger_events={WorkflowEvent.CHECKLIST_COMPLETE},
            auto_advance=True,
        ),
        # Implementation review complete: implementation-review -> verification
        WorkflowTransition(
            from_step="implementation-review",
            to_step="verification",
            trigger_events={WorkflowEvent.MANUAL_ADVANCE},
        ),
        # Skip checklist review: implementation -> verification (manual override)
        WorkflowTransition(
            from_step="implementation",
            to_step="verification",
            trigger_events={WorkflowEvent.MANUAL_ADVANCE},
        ),
        # Verification complete: verification -> commit
        WorkflowTransition(
            from_step="verification",
            to_step="commit",
            trigger_events={WorkflowEvent.MANUAL_ADVANCE},
        ),
        # Commit complete: commit -> pull-request
        WorkflowTransition(
            from_step="commit",
            to_step="pull-request",
            trigger_events={WorkflowEvent.GIT_COMMIT_CREATED, WorkflowEvent.GIT_BRANCH_PUSHED},
            required_tasks=["agdt-git-commit"],
            auto_advance=True,
        ),
        # PR created: pull-request -> completion
        WorkflowTransition(
            from_step="pull-request",
            to_step="completion",
            trigger_events={WorkflowEvent.PR_CREATED},
            required_tasks=["agdt-create-pull-request"],
            auto_advance=True,
        ),
    ],
)

PULL_REQUEST_REVIEW_WORKFLOW = WorkflowDefinition(
    name="pull-request-review",
    initial_step="initiate",
    transitions=[
        # Initiate -> file-review (after PR details fetched)
        WorkflowTransition(
            from_step="initiate",
            to_step="file-review",
            trigger_events={WorkflowEvent.MANUAL_ADVANCE},
        ),
        # File review -> file-review (after each file, if more pending)
        WorkflowTransition(
            from_step="file-review",
            to_step="file-review",
            trigger_events={WorkflowEvent.PR_REVIEWED},
            auto_advance=True,
        ),
        # File review -> summary (when all files done)
        WorkflowTransition(
            from_step="file-review",
            to_step="summary",
            trigger_events={WorkflowEvent.MANUAL_ADVANCE},
        ),
        # Summary -> completion (after summary generated and posted)
        WorkflowTransition(
            from_step="summary",
            to_step="completion",
            trigger_events={WorkflowEvent.MANUAL_ADVANCE},
            required_tasks=["agdt-generate-pr-summary"],
            auto_advance=True,
        ),
    ],
)

# Registry of all workflow definitions
WORKFLOW_REGISTRY: Dict[str, WorkflowDefinition] = {
    "work-on-jira-issue": WORK_ON_JIRA_ISSUE_WORKFLOW,
    "pull-request-review": PULL_REQUEST_REVIEW_WORKFLOW,
    # Other workflows use simple single-step patterns
}


# =============================================================================
# Workflow Manager Functions
# =============================================================================


def get_workflow_definition(workflow_name: str) -> Optional[WorkflowDefinition]:
    """Get the workflow definition by name."""
    return WORKFLOW_REGISTRY.get(workflow_name)


@dataclass
class NotifyEventResult:
    """Result of notify_workflow_event."""

    triggered: bool
    immediate_advance: bool = False
    prompt_rendered: bool = False
    new_step: Optional[str] = None


def notify_workflow_event(
    event: WorkflowEvent,
    task_id: Optional[str] = None,
    context_updates: Optional[Dict[str, Any]] = None,
) -> NotifyEventResult:
    """
    Notify the workflow manager that an event occurred.

    This is called by commands after successful execution to potentially
    trigger a workflow transition.

    Args:
        event: The event that occurred
        task_id: ID of the background task (if any) that completed
        context_updates: Additional context to store in workflow state

    Returns:
        NotifyEventResult with:
        - triggered: True if a transition was matched
        - immediate_advance: True if the transition was executed immediately
        - prompt_rendered: True if a prompt was printed to console
        - new_step: The step we advanced to (if immediate_advance)
    """
    workflow = get_workflow_state()
    if not workflow:
        return NotifyEventResult(triggered=False)

    workflow_name = workflow.get("active")
    current_step = workflow.get("step")
    context = workflow.get("context", {})

    if not workflow_name or not current_step:
        return NotifyEventResult(triggered=False)

    # Get workflow definition
    definition = get_workflow_definition(workflow_name)
    if not definition:
        # Simple workflow without transitions - no auto-advance
        return NotifyEventResult(triggered=False)

    # Find matching transition
    transition = definition.get_transition(current_step, event)
    if not transition:
        return NotifyEventResult(triggered=False)

    # Update context if provided
    if context_updates:
        context.update(context_updates)

    # Record the event in workflow context
    events_log = context.get("events_log", [])
    events_log.append(
        {
            "event": event.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
        }
    )
    context["events_log"] = events_log[-20:]  # Keep last 20 events

    # Check if auto-advance is enabled
    if transition.auto_advance:
        # If no required tasks, execute the transition immediately and render the prompt
        if not transition.required_tasks:
            new_step = transition.to_step

            # Update workflow state to new step
            set_workflow_state(
                name=workflow_name,
                status="in-progress" if new_step != "completion" else "completed",
                step=new_step,
                context=context,
            )

            # Render and print the prompt immediately
            try:
                content = _render_step_prompt(workflow_name, new_step, context)
                print()
                print("=" * 80)
                print(f"WORKFLOW ADVANCED: {workflow_name}")
                print(f"NEW STEP: {new_step}")
                print("=" * 80)
                print()
                _safe_print(content)

                # Show save notice
                temp_dir = get_temp_output_dir()
                saved_path = temp_dir / f"temp-{workflow_name}-{new_step}-prompt.md"
                print()
                print("=" * 80)
                print("The exact prompt logged above is also saved to:")
                print(f"  {saved_path}")
                print("=" * 80)

                return NotifyEventResult(
                    triggered=True,
                    immediate_advance=True,
                    prompt_rendered=True,
                    new_step=new_step,
                )
            except FileNotFoundError as e:
                print(f"\nERROR: Could not load prompt template for step '{new_step}'.", file=sys.stderr)
                print(f"{e}", file=sys.stderr)
                return NotifyEventResult(
                    triggered=True,
                    immediate_advance=True,
                    prompt_rendered=False,
                    new_step=new_step,
                )
        else:
            # Has required tasks - defer to pending_transition for later processing
            context["pending_transition"] = {
                "to_step": transition.to_step,
                "required_tasks": transition.required_tasks,
                "triggered_by": event.value,
            }

    # Save updated context
    set_workflow_state(
        name=workflow_name,
        status=workflow.get("status", "in-progress"),
        step=current_step,
        context=context,
    )

    return NotifyEventResult(triggered=True)


@dataclass
class NextPromptResult:
    """Result of get_next_workflow_prompt."""

    status: PromptStatus
    content: str
    step: Optional[str] = None
    pending_task_ids: Optional[List[str]] = None
    failed_task_ids: Optional[List[str]] = None


def get_next_workflow_prompt() -> NextPromptResult:
    """
    Get the next workflow prompt based on current state.

    This checks:
    1. Is there an active workflow?
    2. Are there pending background tasks that need to complete?
    3. Did any required tasks fail?
    4. Is there a pending transition to execute?

    Returns:
        NextPromptResult with status and appropriate content
    """
    workflow = get_workflow_state()
    if not workflow:
        return NextPromptResult(
            status=PromptStatus.NO_WORKFLOW,
            content="No workflow is currently active.\n\nTo start a workflow, use one of:\n"
            "- agdt-initiate-work-on-jira-issue-workflow\n"
            "- agdt-initiate-pull-request-review-workflow\n"
            "- agdt-initiate-create-jira-issue-workflow",
        )

    workflow_name = workflow.get("active", "")
    current_step = workflow.get("step", "")
    context = workflow.get("context", {})
    pending_transition = context.get("pending_transition")

    # Check for pending background tasks
    pending_tasks = get_active_tasks()
    if pending_tasks:
        pending_ids = [t.id for t in pending_tasks]
        return NextPromptResult(
            status=PromptStatus.WAITING,
            content=_render_waiting_prompt(workflow_name, current_step, pending_tasks),
            step=current_step,
            pending_task_ids=pending_ids,
        )

    # Check for required task failures (if we have a pending transition)
    if pending_transition:
        required_tasks = pending_transition.get("required_tasks", [])
        failed_tasks = _check_required_tasks_status(required_tasks, context)
        if failed_tasks:
            return NextPromptResult(
                status=PromptStatus.FAILURE,
                content=_render_failure_prompt(workflow_name, current_step, failed_tasks),
                step=current_step,
                failed_task_ids=[t["id"] for t in failed_tasks],
            )

        # All required tasks passed - execute the transition
        new_step = pending_transition["to_step"]

        # Clear pending transition by setting to None (so it overrides in merge)
        context["pending_transition"] = None

        # Update workflow state to new step
        set_workflow_state(
            name=workflow_name,
            status="in-progress" if new_step != "completion" else "completed",
            step=new_step,
            context=context,
        )

        # Render and return the prompt for the new step
        try:
            content = _render_step_prompt(workflow_name, new_step, context)
            return NextPromptResult(
                status=PromptStatus.SUCCESS,
                content=content,
                step=new_step,
            )
        except FileNotFoundError as e:
            return NextPromptResult(
                status=PromptStatus.FAILURE,
                content=f"ERROR: Could not load prompt template for step '{new_step}'.\n{e}",
                step=new_step,
            )

    # No pending transition - just return the current step's prompt
    try:
        content = _render_step_prompt(workflow_name, current_step, context)
        return NextPromptResult(
            status=PromptStatus.SUCCESS,
            content=content,
            step=current_step,
        )
    except FileNotFoundError as e:
        return NextPromptResult(
            status=PromptStatus.FAILURE,
            content=f"ERROR: Could not load prompt template for step '{current_step}'.\n{e}",
            step=current_step,
        )


def _check_required_tasks_status(required_task_commands: List[str], context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Check if any required tasks failed.

    Args:
        required_task_commands: List of command names that must succeed
        context: Workflow context containing task IDs

    Returns:
        List of failed task info dictionaries
    """
    failed_tasks = []
    events_log = context.get("events_log", [])

    # Get recent task IDs from events log
    recent_task_ids = [e.get("task_id") for e in events_log if e.get("task_id")]

    for task_id in recent_task_ids:
        task = get_task_by_id(task_id)
        if task and task.status == TaskStatus.FAILED:
            failed_tasks.append(
                {
                    "id": task.id,
                    "command": task.command,
                    "error": task.error_message or "Unknown error",
                    "log_file": task.log_file,
                }
            )

    return failed_tasks


def _build_command_hint(
    command_name: str,
    param_name: str,
    state_key: str,
    current_value: Optional[str],
    is_required: bool = True,
) -> str:
    """
    Build a dynamic command hint based on current state.

    Args:
        command_name: The CLI command (e.g., "agdt-add-jira-comment")
        param_name: The CLI parameter (e.g., "--jira-comment")
        state_key: The state key (e.g., "jira.comment")
        current_value: Current value from state (None if not set)
        is_required: Whether this parameter is required

    Returns:
        A formatted hint string for the prompt
    """
    if current_value:
        # Truncate long values for display
        was_truncated = len(current_value) > 100
        display_value = current_value[:100] + "..." if was_truncated else current_value
        display_value = display_value.replace("\n", "\\n")
        hint = f'`{param_name}` (optional - current `{state_key}`: "{display_value}")'
        if was_truncated:
            hint += f"\n  Use `agdt-get {state_key}` to see the full value."
        return hint
    elif is_required:
        return f"`{param_name}` (REQUIRED - `{state_key}` not set)"
    else:
        return f"`{param_name}` (optional - `{state_key}` not set)"


def _render_step_prompt(workflow_name: str, step_name: str, context: Dict[str, Any]) -> str:
    """
    Render the prompt for a workflow step.

    Args:
        workflow_name: Name of the workflow
        step_name: Name of the step
        context: Workflow context for variable substitution

    Returns:
        Rendered prompt content
    """
    # Build variables from context and state
    variables = dict(context)

    # Add common state values (raw values)
    state_keys = [
        "jira.issue_key",
        "jira.last_issue",
        "jira.comment",
        "pull_request_id",
        "branch_name",
        "source_branch",
        "commit_message",
    ]
    for key in state_keys:
        value = get_value(key)
        if value is not None:
            var_name = key.replace(".", "_")
            variables[var_name] = value

    # For pull-request-review workflow, fetch fresh queue status
    if workflow_name == "pull-request-review":
        pull_request_id = context.get("pull_request_id") or get_value("pull_request_id")
        if pull_request_id:
            try:
                from ..azure_devops.file_review_commands import get_queue_status

                pr_id_int = int(pull_request_id)
                queue_status = get_queue_status(pr_id_int)
                variables["completed_count"] = queue_status["completed_count"]
                variables["pending_count"] = queue_status["pending_count"]
                variables["total_count"] = queue_status["total_count"]
                variables["current_file"] = queue_status["current_file"] or ""
                variables["prompt_file_path"] = queue_status["prompt_file_path"] or ""
                variables["all_complete"] = queue_status["all_complete"]
            except (ImportError, ValueError, TypeError):
                pass  # Use whatever is in context

    # Add shorthand aliases for common variables
    # These provide user-friendly names in templates
    if "jira_issue_key" in variables:
        variables.setdefault("issue_key", variables["jira_issue_key"])

    # Add checklist markdown if checklist exists
    from .checklist import get_checklist

    checklist = get_checklist()
    if checklist:
        variables["checklist_markdown"] = checklist.render_markdown()
    else:
        variables["checklist_markdown"] = "*No checklist created yet*"

    # Extract issue details if available
    last_issue = variables.get("jira_last_issue") or {}
    if isinstance(last_issue, dict):
        fields = last_issue.get("fields", {})
        variables.setdefault("issue_summary", fields.get("summary", ""))
        variables.setdefault("issue_type", fields.get("issuetype", {}).get("name", ""))
        variables.setdefault("issue_labels", ", ".join(fields.get("labels", [])))
        variables.setdefault("issue_description", fields.get("description", ""))

    # Build dynamic command hints for common commands
    jira_comment = get_value("jira.comment")
    get_value("jira.issue_key")
    commit_message = get_value("commit_message")
    get_value("source_branch")

    # Add Jira comment command hint
    variables["add_jira_comment_hint"] = _build_command_hint(
        "agdt-add-jira-comment",
        "--jira-comment",
        "jira.comment",
        jira_comment,
        is_required=True,
    )

    # Add commit command hint
    variables["git_commit_hint"] = _build_command_hint(
        "agdt-git-commit",
        "--commit-message",
        "commit_message",
        commit_message,
        is_required=True,
    )

    # Simple usage examples based on state
    if jira_comment:
        variables["add_jira_comment_usage"] = "agdt-add-jira-comment"
    else:
        variables["add_jira_comment_usage"] = 'agdt-add-jira-comment --jira-comment "<your plan>"'

    if commit_message:
        variables["git_commit_usage"] = "agdt-git-commit"
    else:
        variables["git_commit_usage"] = 'agdt-git-commit --commit-message "<your message>"'

    return load_and_render_prompt(
        workflow_name=workflow_name,
        step_name=step_name,
        variables=variables,
        save_to_temp=True,
        log_output=False,  # Don't double-log
    )


def _render_waiting_prompt(workflow_name: str, step_name: str, pending_tasks: List[Any]) -> str:
    """Render a prompt indicating tasks are still in progress."""
    task_lines = []
    for task in pending_tasks:
        task_lines.append(f"- **{task.command}** (ID: `{task.id[:8]}...`): {task.status.value}")

    return f"""# Workflow: {workflow_name}
## Step: {step_name}

⏳ **Background tasks are still running**

The following tasks are in progress:
{chr(10).join(task_lines)}

## Next Action

Wait for the tasks to complete, then run:

```bash
agdt-get-next-workflow-prompt
```

Or wait for a specific task:

```bash
dfly-set task_id {pending_tasks[0].id}
agdt-task-wait
agdt-get-next-workflow-prompt
```
"""


def _render_failure_prompt(workflow_name: str, step_name: str, failed_tasks: List[Dict[str, Any]]) -> str:
    """Render a prompt indicating task failure."""
    task_lines = []
    for task in failed_tasks:
        task_lines.append(f"### {task['command']}")
        task_lines.append(f"- **Error**: {task['error']}")
        if task.get("log_file"):
            task_lines.append(f"- **Log file**: `{task['log_file']}`")
        task_lines.append("")

    return f"""# Workflow: {workflow_name}
## Step: {step_name}

❌ **One or more background tasks failed**

{chr(10).join(task_lines)}

## Suggested Actions

1. **View the full log**:
   ```bash
   agdt-set task_id <task-id>
   agdt-task-log
   ```

2. **Fix the issue** and retry the command

3. **After fixing**, continue the workflow:
   ```bash
   agdt-get-next-workflow-prompt
   ```
"""


# =============================================================================
# CLI Command Entry Points
# =============================================================================


def get_next_workflow_prompt_cmd() -> None:
    """
    CLI command to get the next workflow prompt.

    Usage: agdt-get-next-workflow-prompt

    This checks background task status and returns:
    - The next step's prompt if all tasks succeeded
    - A waiting prompt if tasks are still running
    - A failure prompt if any task failed
    - A no-workflow message if no workflow is active
    """
    result = get_next_workflow_prompt()

    # Print status header
    print("=" * 80)
    print(f"WORKFLOW PROMPT STATUS: {result.status.value.upper()}")
    if result.step:
        print(f"STEP: {result.step}")
    print("=" * 80)
    print()

    # Print content
    _safe_print(result.content)

    # Show save notice for successful prompts with a known step
    if result.status == PromptStatus.SUCCESS and result.step:
        workflow = get_workflow_state()
        if workflow:
            workflow_name = workflow.get("active", "")
            if workflow_name:
                temp_dir = get_temp_output_dir()
                saved_path = temp_dir / f"temp-{workflow_name}-{result.step}-prompt.md"
                print()
                print("=" * 80)
                print("The exact prompt logged above is also saved to:")
                print(f"  {saved_path}")
                print("=" * 80)

    # Exit with appropriate code
    if result.status == PromptStatus.FAILURE:
        sys.exit(1)
    elif result.status == PromptStatus.WAITING:
        sys.exit(2)  # Special exit code for waiting
