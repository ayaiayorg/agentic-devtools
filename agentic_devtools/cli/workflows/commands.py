"""
Workflow CLI commands.

This module provides CLI entry points for all workflow initiation commands.
Each command:
1. Validates required state
2. Loads and renders the appropriate prompt template
3. Updates workflow state
4. Logs the prompt to console with save notice

The work-on-jira-issue workflow uses a state-machine approach with:
- Pre-flight checks for worktree/branch validation
- Step-specific micro-prompts
- Automatic workflow advancement from commands
"""

import sys
from typing import List, Optional

from .base import (
    advance_workflow_step,
    clear_state_for_workflow_initiation,
    initiate_workflow,
    validate_required_state,
)
from .preflight import check_worktree_and_branch


def initiate_pull_request_review_workflow(
    pull_request_id: Optional[str] = None,
    issue_key: Optional[str] = None,
    interactive: Optional[bool] = None,
    _argv: Optional[List[str]] = None,
) -> None:
    """
    Initiate the pull request review workflow.

    Can be started with either a pull request ID or a Jira issue key.
    If issue key is provided, searches for an active PR with that issue key
    in the source branch name.

    If not in the correct worktree/branch context, automatically creates
    a worktree, installs agentic-devtools, and opens VS Code, then starts
    a gh copilot session with the integrated review prompt.

    Usage:
        agdt-initiate-pull-request-review-workflow --pull-request-id 12345
        agdt-initiate-pull-request-review-workflow --issue-key DFLY-1234
        agdt-initiate-pull-request-review-workflow --pull-request-id 12345 --interactive false

    Args:
        pull_request_id: ID of the pull request to review.
        issue_key: Jira issue key to find the PR by branch name.
        interactive: Whether to start the Copilot session interactively (default: True).
            Set to False for pipeline/non-interactive mode.
        _argv: Command line arguments (for testing). Pass [] in tests to avoid parsing sys.argv
            (this function always calls parse_known_args, so unknown flags are silently ignored,
            but passing [] prevents any accidental parsing of the test runner's sys.argv).

    Either pull_request_id or issue_key must be provided (via CLI or state).
    """
    # Clear all previous state to ensure fresh workflow start
    clear_state_for_workflow_initiation()

    import argparse

    from ...state import get_value, set_value
    from ..azure_devops.helpers import find_jira_issue_from_pr, find_pr_from_jira_issue, get_pull_request_source_branch
    from .preflight import perform_auto_setup

    # Parse CLI arguments — always parse to pick up --interactive even when
    # pull_request_id/issue_key are supplied programmatically.
    parser = argparse.ArgumentParser(
        description="Initiate the pull request review workflow",
        epilog="""
Examples:
  agdt-initiate-pull-request-review-workflow --pull-request-id 12345
  agdt-initiate-pull-request-review-workflow --issue-key DFLY-1234
  agdt-initiate-pull-request-review-workflow --pull-request-id 12345 --issue-key DFLY-1234
  agdt-initiate-pull-request-review-workflow --pull-request-id 12345 --interactive false
        """,
    )
    parser.add_argument(
        "--pull-request-id",
        "-p",
        dest="pull_request_id",
        help="ID of the pull request to review.",
    )
    parser.add_argument(
        "--issue-key",
        "-i",
        dest="issue_key",
        help="Jira issue key to find PR by branch name (e.g., DFLY-1234).",
    )
    parser.add_argument(
        "--interactive",
        dest="interactive",
        default=None,
        help="Start Copilot session interactively (default: true). Pass 'false' for pipeline mode.",
    )
    args, _unknown = parser.parse_known_args(_argv)

    # CLI values override programmatic values only when not already set
    if pull_request_id is None and args.pull_request_id:
        pull_request_id = args.pull_request_id
    if issue_key is None and args.issue_key:
        issue_key = args.issue_key
    if interactive is None and args.interactive is not None:
        interactive = args.interactive.lower() not in ("false", "0", "no")
    if interactive is None:
        interactive = True

    # Set provided values in state (use set_value directly since we handle cross-lookup below)
    if pull_request_id:
        set_value("pull_request_id", pull_request_id)
    if issue_key:
        set_value("jira.issue_key", issue_key)

    # Get resolved values from state
    resolved_pr_id = get_value("pull_request_id")
    resolved_issue_key = get_value("jira.issue_key")

    # Cross-lookup: If we have one but not the other, look up the missing one
    if resolved_pr_id and not resolved_issue_key:
        # We have PR ID but no issue key -> look up from PR
        print(f"Looking up Jira issue from PR #{resolved_pr_id}...")
        found_issue = find_jira_issue_from_pr(int(resolved_pr_id))
        if found_issue:  # pragma: no cover
            resolved_issue_key = found_issue
            set_value("jira.issue_key", resolved_issue_key)
            print(f"✓ Found Jira issue {resolved_issue_key} from PR")
        else:
            print("ℹ️  No Jira issue key found in PR branch/title/description")

    elif resolved_issue_key and not resolved_pr_id:
        # We have issue key but no PR ID -> look up from Jira/ADO
        print(f"Searching for PR linked to Jira issue '{resolved_issue_key}'...")
        found_pr = find_pr_from_jira_issue(resolved_issue_key, verbose=True)
        if found_pr:
            resolved_pr_id = str(found_pr)
            set_value("pull_request_id", resolved_pr_id)
            print(f"✓ Found PR #{resolved_pr_id}")
        else:
            print(f"ERROR: No active PR found for issue key '{resolved_issue_key}'")
            print("\nSearched in:")
            print("  - Jira issue comments and description")
            print("  - Azure DevOps PR source branch, title, and description")
            print("\nTo find a completed PR, use:")
            print(f"  agdt-find-pr-by-issue --issue-key {resolved_issue_key} --status all")
            sys.exit(1)

    # Validate we have a PR ID now
    if not resolved_pr_id:
        print("ERROR: Either --pull-request-id or --issue-key must be provided.")
        print("\nUsage:")
        print("  agdt-initiate-pull-request-review-workflow --pull-request-id 12345")
        print("  agdt-initiate-pull-request-review-workflow --issue-key DFLY-1234")
        sys.exit(1)

    # For PR review workflows, we need to know the source branch BEFORE creating
    # the worktree, so we can checkout that branch instead of creating a new one.
    # Fetch PR details early to get the source branch.
    source_branch: Optional[str] = None
    try:
        source_branch = get_pull_request_source_branch(int(resolved_pr_id))
        if source_branch:
            print(f"PR source branch: {source_branch}")
    except Exception as e:
        print(f"Error: Could not fetch PR source branch: {e}", file=sys.stderr)

    # For PR review, we MUST have the source branch to checkout the correct code
    if not source_branch:
        print(
            f"\nError: Unable to determine source branch for PR #{resolved_pr_id}.",
            file=sys.stderr,
        )
        print("This is required to checkout the correct code for review.", file=sys.stderr)
        print("\nPossible causes:", file=sys.stderr)
        print("  - Azure CLI not authenticated (run 'az login')", file=sys.stderr)
        print("  - Network issues or Azure DevOps API unavailable", file=sys.stderr)
        print(f"  - PR #{resolved_pr_id} does not exist or is not accessible", file=sys.stderr)
        sys.exit(1)

    # Determine the worktree folder identifier
    # Use Jira issue key if available, otherwise use PR{pr_id} format
    worktree_identifier = resolved_issue_key if resolved_issue_key else f"PR{resolved_pr_id}"

    # Check if we're in the correct worktree/branch context
    # For PR reviews, also pass source_branch so branch validation can match on exact branch name
    # (important when no Jira issue - folder is PR{id} but branch is the actual PR source branch)
    preflight_result = check_worktree_and_branch(worktree_identifier, source_branch=source_branch)

    if not preflight_result.passed:
        print(f"\n⚠️  Not in the correct context for {worktree_identifier}")
        for reason in preflight_result.failure_reasons:
            print(f"   - {reason}")

        # Build the command to re-run inside the worktree so the full setup
        # (fetch PR details, generate prompts, init workflow state) executes there.
        auto_execute_command = [
            "agdt-initiate-pull-request-review-workflow",
            "--pull-request-id",
            str(resolved_pr_id),
        ]
        if resolved_issue_key:
            auto_execute_command.extend(["--issue-key", resolved_issue_key])

        # Automatically set up the environment with the PR's source branch
        if perform_auto_setup(
            worktree_identifier,
            "pull-request-review",
            branch_name=source_branch,
            use_existing_branch=True if source_branch else False,
            additional_params={"pull_request_id": resolved_pr_id} if resolved_pr_id else None,
            auto_execute_command=auto_execute_command,
            interactive=interactive,
        ):
            # Setup successful - user should continue in new VS Code window
            print("\n" + "=" * 80)
            print("Please continue the workflow in the new VS Code window.")
            print("=" * 80)
            return
        else:
            # Setup failed - exit with error
            sys.exit(1)  # pragma: no cover

    # Start background task to set up the PR review workflow
    # This fetches PR details, checks out the branch, generates prompts/queue,
    # and initializes the workflow state.
    from ..azure_devops.async_commands import setup_pull_request_review_async

    print(f"\nInitiating pull request review for PR #{resolved_pr_id}...")
    setup_pull_request_review_async(
        pull_request_id=int(resolved_pr_id),
        jira_issue_key=resolved_issue_key,
    )


def initiate_work_on_jira_issue_workflow(
    issue_key: Optional[str] = None,
    _argv: Optional[List[str]] = None,
) -> None:
    """
    Initiate the work-on-jira-issue workflow with pre-flight checks.

    This workflow uses a state-machine approach:
    1. Pre-flight: Validates worktree folder & branch contain issue key
    2. Auto-setup (if preflight fails): Creates worktree, installs helpers, opens VS Code
    3. Retrieve (if preflight passes): Auto-fetches Jira issue details
    4. Planning: Analyze issue and post plan comment
    5. Implementation: Code changes, tests, docs
    6. Verification: Run tests and quality gates
    7. Commit: Stage and commit changes
    8. Pull-request: Create PR
    9. Completion: Post final Jira comment

    If not in the correct worktree/branch context, automatically creates
    a worktree, installs agentic-devtools, and opens VS Code.

    Usage: agdt-initiate-work-on-jira-issue-workflow [--issue-key DFLY-1234]

    Args:
        issue_key: Jira issue key (e.g., DFLY-1234). If not provided, uses jira.issue_key from state.
        _argv: Command line arguments (for testing). Pass [] to skip CLI parsing.
    """
    # Clear all previous state to ensure fresh workflow start
    clear_state_for_workflow_initiation()

    import argparse

    from ...state import set_value
    from .preflight import perform_auto_setup

    # Parse CLI arguments if not called programmatically
    if issue_key is None:
        parser = argparse.ArgumentParser(description="Initiate the work-on-jira-issue workflow")
        parser.add_argument(
            "--issue-key",
            dest="issue_key",
            help="Jira issue key (e.g., DFLY-1234). If not provided, uses jira.issue_key from state.",
        )
        args = parser.parse_args(_argv)
        issue_key = args.issue_key

    # If issue_key provided via CLI, set it in state
    if issue_key:  # pragma: no cover
        set_value("jira.issue_key", issue_key)
    else:
        # Validate required state if no issue_key provided
        required_values = validate_required_state(["jira.issue_key"])
        issue_key = required_values["jira.issue_key"]

    # Run pre-flight checks
    preflight_result = check_worktree_and_branch(issue_key)

    if not preflight_result.passed:
        print(f"\n⚠️  Not in the correct context for issue {issue_key}")
        for reason in preflight_result.failure_reasons:
            print(f"   - {reason}")

        # Automatically set up the environment
        if perform_auto_setup(issue_key, "work-on-jira-issue"):
            # Setup successful - user should continue in new VS Code window
            print("\n" + "=" * 80)
            print("Please continue the workflow in the new VS Code window.")
            print("=" * 80)
            return
        else:
            # Setup failed - exit with error
            sys.exit(1)  # pragma: no cover

    # Pre-flight passed - proceed to retrieve step
    _execute_retrieve_step(issue_key, preflight_result.branch_name)


def _execute_retrieve_step(issue_key: str, branch_name: str) -> None:
    """
    Execute the retrieve step: fetch Jira issue and advance to planning.

    Args:
        issue_key: The Jira issue key
        branch_name: Current git branch name
    """
    from ...state import set_workflow_state

    # Set workflow state to retrieve step
    set_workflow_state(
        name="work-on-jira-issue",
        status="in-progress",
        step="retrieve",
        context={
            "jira_issue_key": issue_key,
            "branch_name": branch_name,
        },
    )

    # Fetch Jira issue synchronously (not via background task)
    # We need the results immediately to proceed with workflow
    print(f"Fetching Jira issue {issue_key}...")
    try:
        from ..jira.get_commands import get_issue
        from ..jira.state_helpers import set_jira_value

        # Ensure issue key is set in jira state
        set_jira_value("issue_key", issue_key)

        # Call get_issue synchronously - this prints details and saves to temp file
        get_issue()
    except SystemExit:
        # get_issue calls sys.exit(1) on failure
        print(f"Warning: Failed to fetch issue {issue_key}. Proceeding with limited context.", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Could not fetch Jira issue: {e}", file=sys.stderr)

    # Get issue details from the temp file (get_issue saves full JSON there)
    # The state only stores metadata reference, not the actual issue data
    from ...state import get_state_dir

    issue_file = get_state_dir() / "temp-get-issue-details-response.json"
    issue_data = {}
    if issue_file.exists():
        try:
            import json

            issue_data = json.loads(issue_file.read_text(encoding="utf-8"))
        except Exception as e:  # pragma: no cover
            print(f"Warning: Could not read issue file: {e}", file=sys.stderr)

    fields = issue_data.get("fields", {})

    issue_summary = fields.get("summary", "No summary available")
    issue_type = fields.get("issuetype", {}).get("name", "Unknown")
    issue_labels = ", ".join(fields.get("labels", [])) or "None"
    issue_description = fields.get("description", "No description available")

    # Format comments
    comments_data = fields.get("comment", {}).get("comments", [])
    if comments_data:
        comment_lines = []
        for c in comments_data[-5:]:  # Last 5 comments
            author = c.get("author", {}).get("displayName", "Unknown")
            body = c.get("body", "")[:200]  # First 200 chars
            comment_lines.append(f"**{author}**: {body}...")
        issue_comments = "\n".join(comment_lines)
    else:
        issue_comments = "No comments"

    # Output retrieve prompt (brief summary)
    print("\n" + "=" * 80)
    print("WORKFLOW: work-on-jira-issue")
    print("STEP: retrieve")
    print("=" * 80)
    print(f"\nIssue {issue_key} retrieved successfully.")
    print(f"Summary: {issue_summary}")
    print(f"Type: {issue_type}")
    print("=" * 80)

    # Automatically advance to planning step
    _execute_planning_step(
        issue_key=issue_key,
        branch_name=branch_name,
        issue_summary=issue_summary,
        issue_type=issue_type,
        issue_labels=issue_labels,
        issue_description=issue_description,
        issue_comments=issue_comments,
    )


def _execute_planning_step(
    issue_key: str,
    branch_name: str,
    issue_summary: str,
    issue_type: str,
    issue_labels: str,
    issue_description: str,
    issue_comments: str,
) -> None:
    """
    Execute the planning step: output planning prompt.

    Args:
        issue_key: The Jira issue key
        branch_name: Current git branch name
        issue_summary: Issue summary from Jira
        issue_type: Issue type
        issue_labels: Comma-separated labels
        issue_description: Full issue description
        issue_comments: Formatted recent comments
    """
    from ...state import set_workflow_state

    # Update workflow state to planning
    set_workflow_state(
        name="work-on-jira-issue",
        status="in-progress",
        step="planning",
        context={
            "jira_issue_key": issue_key,
            "branch_name": branch_name,
            "issue_summary": issue_summary,
        },
    )

    # Build dynamic command hints based on current state
    from ...state import get_value
    from .manager import _build_command_hint

    jira_comment = get_value("jira.comment")

    add_jira_comment_hint = _build_command_hint(
        "agdt-add-jira-comment",
        "--jira-comment",
        "jira.comment",
        jira_comment,
        is_required=True,
    )

    if jira_comment:  # pragma: no cover
        add_jira_comment_usage = "agdt-add-jira-comment"
    else:
        add_jira_comment_usage = 'agdt-add-jira-comment --jira-comment "<your plan>"'

    # Output planning prompt
    initiate_workflow(
        workflow_name="work-on-jira-issue",
        required_state_keys=[],
        optional_state_keys=[],
        additional_variables={
            "issue_key": issue_key,
            "issue_summary": issue_summary,
            "issue_type": issue_type,
            "issue_labels": issue_labels,
            "issue_description": issue_description,
            "issue_comments": issue_comments,
            "branch_name": branch_name,
            "add_jira_comment_hint": add_jira_comment_hint,
            "add_jira_comment_usage": add_jira_comment_usage,
        },
        step_name="planning",
        context={
            "jira_issue_key": issue_key,
            "branch_name": branch_name,
            "issue_summary": issue_summary,
        },
    )


def advance_work_on_jira_issue_workflow(step: Optional[str] = None) -> None:
    """
    Advance the work-on-jira-issue workflow to the next step.

    Usage: agdt-advance-workflow <step>

    Steps: implementation, verification, commit, pull-request, completion

    Args:
        step: The step to advance to (optional, auto-detects next step if not provided)
    """
    from ...state import get_value, get_workflow_state, is_workflow_active

    if not is_workflow_active("work-on-jira-issue"):
        print("ERROR: work-on-jira-issue workflow is not active.", file=sys.stderr)
        print("Start it with: agdt-initiate-work-on-jira-issue-workflow", file=sys.stderr)
        sys.exit(1)

    workflow = get_workflow_state()
    if not workflow:
        print("ERROR: Could not get workflow state.", file=sys.stderr)
        sys.exit(1)

    context = workflow.get("context", {})
    current_step = workflow.get("step", "")
    issue_key = context.get("jira_issue_key", get_value("jira.issue_key") or "")
    branch_name = context.get("branch_name", "")
    issue_summary = context.get("issue_summary", "")

    # Determine next step if not specified
    step_order = [
        "planning",
        "checklist-creation",
        "implementation",
        "implementation-review",
        "verification",
        "commit",
        "pull-request",
        "completion",
    ]
    if step is None:
        try:
            current_idx = step_order.index(current_step)
            step = step_order[current_idx + 1] if current_idx + 1 < len(step_order) else "completion"
        except ValueError:
            step = "implementation"

    # Get PR info if available (for completion step)
    pull_request_id = get_value("pull_request_id") or context.get("pull_request_id", "")
    pull_request_url = context.get("pull_request_url", "")

    # Build variables for the step
    variables = {
        "issue_key": issue_key,
        "issue_summary": issue_summary,
        "branch_name": branch_name,
        "pull_request_id": pull_request_id,
        "pull_request_url": pull_request_url,
    }

    advance_workflow_step(
        workflow_name="work-on-jira-issue",
        step_name=step,
        variables=variables,
        status="in-progress" if step != "completion" else "completed",
    )


def advance_pull_request_review_workflow(step: Optional[str] = None) -> None:
    """
    Advance the pull-request-review workflow to the next step.

    Usage: agdt-advance-workflow <step>

    Steps: file-review, summary, decision, completion

    Args:
        step: The step to advance to (optional, auto-detects next step if not provided)
    """
    from ...state import get_value, get_workflow_state, is_workflow_active
    from ..azure_devops.file_review_commands import get_queue_status

    if not is_workflow_active("pull-request-review"):
        print("ERROR: pull-request-review workflow is not active.", file=sys.stderr)
        print("Start it with: agdt-review-pull-request", file=sys.stderr)
        sys.exit(1)

    workflow = get_workflow_state()
    if not workflow:
        print("ERROR: Could not get workflow state.", file=sys.stderr)
        sys.exit(1)

    context = workflow.get("context", {})
    current_step = workflow.get("step", "")

    # Get PR ID from context or state
    pull_request_id = context.get("pull_request_id") or get_value("pull_request_id")
    if not pull_request_id:
        print("ERROR: No pull_request_id found in workflow context or state.", file=sys.stderr)
        sys.exit(1)

    # Convert to int if string
    try:
        pr_id_int = int(pull_request_id)
    except (TypeError, ValueError):
        print(f"ERROR: Invalid pull_request_id: {pull_request_id}", file=sys.stderr)
        sys.exit(1)

    # Get queue status for file-review step
    queue_status = get_queue_status(pr_id_int)

    if step is None:
        # Auto-detect next step based on current step and queue status
        if current_step == "initiate":
            step = "file-review"
        elif current_step == "file-review":
            # If all files are complete, go to summary; otherwise stay in file-review
            if queue_status["all_complete"]:
                step = "summary"
            else:
                step = "file-review"
        elif current_step == "summary":  # pragma: no cover
            step = "decision"
        elif current_step == "decision":  # pragma: no cover
            step = "completion"
        else:  # pragma: no cover
            # Default to file-review
            step = "file-review"

    # Build variables for the step
    jira_issue_key = context.get("jira_issue_key") or get_value("jira.issue_key") or ""
    pr_title = context.get("pr_title", "")
    pr_author = context.get("pr_author", "")
    source_branch = context.get("source_branch", "")
    target_branch = context.get("target_branch", "")
    file_count = context.get("file_count", queue_status["total_count"])

    variables = {
        "pull_request_id": pull_request_id,
        "jira_issue_key": jira_issue_key,
        "pr_title": pr_title,
        "pr_author": pr_author,
        "source_branch": source_branch,
        "target_branch": target_branch,
        "file_count": file_count,
        # Queue status variables (for file-review step)
        "completed_count": queue_status["completed_count"],
        "pending_count": queue_status["pending_count"],
        "total_count": queue_status["total_count"],
        "current_file": queue_status["current_file"] or "",
        "prompt_file_path": queue_status["prompt_file_path"] or "",
        "all_complete": queue_status["all_complete"],
    }

    advance_workflow_step(
        workflow_name="pull-request-review",
        step_name=step,
        variables=variables,
        status="in-progress" if step != "completion" else "completed",
    )


def initiate_create_jira_issue_workflow(
    project_key: Optional[str] = None,
    issue_key: Optional[str] = None,
    issue_type: Optional[str] = None,
    user_request: Optional[str] = None,
    _argv: Optional[List[str]] = None,
) -> None:
    """
    Initiate the create-jira-issue workflow.

    If no issue_key is provided, creates a placeholder issue in Jira first,
    then sets up a worktree and opens VS Code for the user to continue.

    If issue_key is provided (after worktree setup), continues the workflow
    to populate the issue with full details based on the user's request.

    Usage:
        # Initial call - creates placeholder and sets up worktree:
        agdt-initiate-create-jira-issue-workflow --user-request "I need a story to..."

        # With custom issue type:
        agdt-initiate-create-jira-issue-workflow --issue-type Task --user-request "I need a task to..."

        # Continuation call in new VS Code window:
        agdt-initiate-create-jira-issue-workflow --issue-key DFLY-1234 --user-request "..."

    Args:
        project_key: Jira project key (e.g., DFLY). If not provided, uses jira.project_key from state.
        issue_key: Issue key (provided after placeholder creation for continuation).
        issue_type: Jira issue type (e.g., Story, Task, Bug). Defaults to "Story".
        user_request: User's explanation of what they want. The AI agent will use this
            to populate all Jira fields (summary, description, acceptance criteria, etc.).
        _argv: Command line arguments (for testing). Pass [] to skip CLI parsing.

    Optional state:
    - jira.user_request: User's explanation of what they want
    - jira.summary: Issue summary (AI-generated from user_request)
    - jira.description: Issue description (AI-generated from user_request)
    - jira.issue_type: Issue type (defaults to "Story")
    """
    # Clear all previous state to ensure fresh workflow start
    clear_state_for_workflow_initiation()

    import argparse

    from ...state import get_value, set_value
    from .preflight import check_worktree_and_branch, perform_auto_setup
    from .worktree_setup import create_placeholder_and_setup_worktree

    # Parse CLI arguments if not called programmatically
    if project_key is None and issue_key is None and issue_type is None and user_request is None:
        parser = argparse.ArgumentParser(description="Initiate the create-jira-issue workflow")
        parser.add_argument(
            "--project-key",
            dest="project_key",
            help="Jira project key (e.g., DFLY). If not provided, uses jira.project_key from state.",
        )
        parser.add_argument(
            "--issue-key",
            "-i",
            dest="issue_key",
            help="Issue key (provided after placeholder creation for continuation).",
        )
        parser.add_argument(
            "--issue-type",
            "-t",
            dest="issue_type",
            help="Jira issue type (e.g., Story, Task, Bug). Defaults to 'Story'.",
        )
        parser.add_argument(
            "--user-request",
            "-u",
            dest="user_request",
            help="Your explanation of what you want. AI will use this to populate all Jira fields.",
        )
        args = parser.parse_args(_argv)
        project_key = args.project_key
        issue_key = args.issue_key
        issue_type = args.issue_type
        user_request = args.user_request

    # If project_key provided via CLI, set it in state
    if project_key:  # pragma: no cover
        set_value("jira.project_key", project_key)

    # If issue_key provided via CLI, set it in state
    if issue_key:  # pragma: no cover
        set_value("jira.issue_key", issue_key)

    # If issue_type provided via CLI, set it in state
    if issue_type:  # pragma: no cover
        set_value("jira.issue_type", issue_type)

    # If user_request provided via CLI, set it in state
    if user_request:  # pragma: no cover
        set_value("jira.user_request", user_request)

    # Get resolved values from state
    resolved_issue_key = get_value("jira.issue_key")
    resolved_project_key = get_value("jira.project_key") or "DFLY"
    resolved_issue_type = get_value("jira.issue_type") or "Story"
    resolved_user_request = get_value("jira.user_request")

    # If we have an issue key, check if we're in the right context
    if resolved_issue_key:
        preflight_result = check_worktree_and_branch(resolved_issue_key)

        if preflight_result.passed:
            # We're in the correct context - proceed with the workflow
            initiate_workflow(
                workflow_name="create-jira-issue",
                required_state_keys=["jira.project_key"],
                optional_state_keys=[
                    "jira.summary",
                    "jira.description",
                    "jira.issue_key",
                    "jira.issue_type",
                    "jira.user_request",
                ],
            )
            return
        else:
            # Not in correct context - auto-setup
            print(f"\n⚠️  Not in the correct context for issue {resolved_issue_key}")
            for reason in preflight_result.failure_reasons:
                print(f"   - {reason}")

            if perform_auto_setup(resolved_issue_key, "create-jira-issue", user_request=resolved_user_request):
                print("\n" + "=" * 80)
                print("Please continue the workflow in the new VS Code window.")
                print("=" * 80)
                return
            else:
                sys.exit(1)

    # No issue key - create placeholder and set up worktree
    success, created_issue_key = create_placeholder_and_setup_worktree(
        project_key=resolved_project_key,
        issue_type=resolved_issue_type,
        workflow_name="create-jira-issue",
        user_request=resolved_user_request,
    )

    if success:
        print("\n" + "=" * 80)
        print("Please continue the workflow in the new VS Code window.")
        print("=" * 80)
    else:
        sys.exit(1)


def initiate_create_jira_epic_workflow(
    project_key: Optional[str] = None,
    issue_key: Optional[str] = None,
    user_request: Optional[str] = None,
    _argv: Optional[List[str]] = None,
) -> None:
    """
    Initiate the create-jira-epic workflow.

    If no issue_key is provided, creates a placeholder Epic in Jira first,
    then sets up a worktree and opens VS Code for the user to continue.

    If issue_key is provided (after worktree setup), continues the workflow
    to populate the epic with full details based on the user's request.

    Usage:
        # Initial call - creates placeholder and sets up worktree:
        agdt-initiate-create-jira-epic-workflow --user-request "I need an epic for..."

        # Continuation call in new VS Code window:
        agdt-initiate-create-jira-epic-workflow --issue-key DFLY-1234 --user-request "..."

    Args:
        project_key: Jira project key (e.g., DFLY). If not provided, uses jira.project_key from state.
        issue_key: Issue key (provided after placeholder creation for continuation).
        user_request: User's explanation of what they want. The AI agent will use this
            to populate all Jira fields (summary, epic name, description, user story, etc.).
        _argv: Command line arguments (for testing). Pass [] to skip CLI parsing.

    Optional state:
    - jira.user_request: User's explanation of what they want
    - jira.summary: Epic summary (AI-generated from user_request)
    - jira.epic_name: Epic name (AI-generated from user_request)
    - jira.role: User role for the user story
    - jira.desired_outcome: Desired outcome for the user story
    - jira.benefit: Benefit for the user story
    """
    # Clear all previous state to ensure fresh workflow start
    clear_state_for_workflow_initiation()

    import argparse

    from ...state import get_value, set_value
    from .preflight import check_worktree_and_branch, perform_auto_setup
    from .worktree_setup import create_placeholder_and_setup_worktree

    # Parse CLI arguments if not called programmatically
    if project_key is None and issue_key is None and user_request is None:
        parser = argparse.ArgumentParser(description="Initiate the create-jira-epic workflow")
        parser.add_argument(
            "--project-key",
            dest="project_key",
            help="Jira project key (e.g., DFLY). If not provided, uses jira.project_key from state.",
        )
        parser.add_argument(
            "--issue-key",
            "-i",
            dest="issue_key",
            help="Issue key (provided after placeholder creation for continuation).",
        )
        parser.add_argument(
            "--user-request",
            "-u",
            dest="user_request",
            help="Your explanation of what you want. AI will use this to populate all Jira fields.",
        )
        args = parser.parse_args(_argv)
        project_key = args.project_key
        issue_key = args.issue_key
        user_request = args.user_request

    # If project_key provided via CLI, set it in state
    if project_key:  # pragma: no cover
        set_value("jira.project_key", project_key)

    # If issue_key provided via CLI, set it in state
    if issue_key:  # pragma: no cover
        set_value("jira.issue_key", issue_key)

    # If user_request provided via CLI, set it in state
    if user_request:  # pragma: no cover
        set_value("jira.user_request", user_request)

    # Get resolved values from state
    resolved_issue_key = get_value("jira.issue_key")
    resolved_project_key = get_value("jira.project_key") or "DFLY"
    resolved_user_request = get_value("jira.user_request")

    # If we have an issue key, check if we're in the right context
    if resolved_issue_key:
        preflight_result = check_worktree_and_branch(resolved_issue_key)

        if preflight_result.passed:
            # We're in the correct context - proceed with the workflow
            initiate_workflow(
                workflow_name="create-jira-epic",
                required_state_keys=["jira.project_key"],
                optional_state_keys=[
                    "jira.summary",
                    "jira.epic_name",
                    "jira.role",
                    "jira.desired_outcome",
                    "jira.benefit",
                    "jira.issue_key",
                    "jira.user_request",
                ],
            )
            return
        else:
            # Not in correct context - auto-setup
            print(f"\n⚠️  Not in the correct context for issue {resolved_issue_key}")
            for reason in preflight_result.failure_reasons:
                print(f"   - {reason}")

            if perform_auto_setup(resolved_issue_key, "create-jira-epic", user_request=resolved_user_request):
                print("\n" + "=" * 80)
                print("Please continue the workflow in the new VS Code window.")
                print("=" * 80)
                return
            else:
                sys.exit(1)

    # No issue key - create placeholder and set up worktree
    success, created_issue_key = create_placeholder_and_setup_worktree(
        project_key=resolved_project_key,
        issue_type="Epic",
        workflow_name="create-jira-epic",
        user_request=resolved_user_request,
    )

    if success:
        print("\n" + "=" * 80)
        print("Please continue the workflow in the new VS Code window.")
        print("=" * 80)
    else:
        sys.exit(1)


def initiate_create_jira_subtask_workflow(
    parent_key: Optional[str] = None,
    issue_key: Optional[str] = None,
    user_request: Optional[str] = None,
    _argv: Optional[List[str]] = None,
) -> None:
    """
    Initiate the create-jira-subtask workflow.

    If no issue_key is provided, creates a placeholder Sub-task in Jira first,
    then sets up a worktree and opens VS Code for the user to continue.

    If issue_key is provided (after worktree setup), continues the workflow
    to populate the subtask with full details based on the user's request.

    Usage:
        # Initial call - creates placeholder and sets up worktree:
        agdt-initiate-create-jira-subtask-workflow --parent-key DFLY-1234 --user-request "I need a subtask to..."

        # Continuation call in new VS Code window:
        agdt-initiate-create-jira-subtask-workflow --issue-key DFLY-1235 --user-request "..."

    Args:
        parent_key: Parent issue key (e.g., DFLY-1234). Required for creating placeholder.
        issue_key: Issue key (provided after placeholder creation for continuation).
        user_request: User's explanation of what they want. The AI agent will use this
            to populate all Jira fields (summary, description, etc.).
        _argv: Command line arguments (for testing). Pass [] to skip CLI parsing.

    Optional state:
    - jira.user_request: User's explanation of what they want
    - jira.summary: Subtask summary (AI-generated from user_request)
    - jira.description: Subtask description (AI-generated from user_request)
    """
    # Clear all previous state to ensure fresh workflow start
    clear_state_for_workflow_initiation()

    import argparse

    from ...state import get_value, set_value
    from .preflight import check_worktree_and_branch, perform_auto_setup
    from .worktree_setup import create_placeholder_and_setup_worktree

    # Parse CLI arguments if not called programmatically
    if parent_key is None and issue_key is None and user_request is None:
        parser = argparse.ArgumentParser(description="Initiate the create-jira-subtask workflow")
        parser.add_argument(
            "--parent-key",
            dest="parent_key",
            help="Parent issue key (e.g., DFLY-1234). If not provided, uses jira.parent_key from state.",
        )
        parser.add_argument(
            "--issue-key",
            "-i",
            dest="issue_key",
            help="Issue key (provided after placeholder creation for continuation).",
        )
        parser.add_argument(
            "--user-request",
            "-u",
            dest="user_request",
            help="Your explanation of what you want. AI will use this to populate all Jira fields.",
        )
        args = parser.parse_args(_argv)
        parent_key = args.parent_key
        issue_key = args.issue_key
        user_request = args.user_request

    # If parent_key provided via CLI, set it in state
    if parent_key:
        set_value("jira.parent_key", parent_key)

    # If issue_key provided via CLI, set it in state
    if issue_key:
        set_value("jira.issue_key", issue_key)

    # If user_request provided via CLI, set it in state
    if user_request:  # pragma: no cover
        set_value("jira.user_request", user_request)

    # Get resolved values from state
    resolved_issue_key = get_value("jira.issue_key")
    resolved_parent_key = get_value("jira.parent_key")
    resolved_user_request = get_value("jira.user_request")

    # If we have an issue key, check if we're in the right context
    if resolved_issue_key:
        preflight_result = check_worktree_and_branch(resolved_issue_key)

        if preflight_result.passed:
            # We're in the correct context - proceed with the workflow
            initiate_workflow(
                workflow_name="create-jira-subtask",
                required_state_keys=["jira.parent_key"],
                optional_state_keys=["jira.summary", "jira.description", "jira.issue_key", "jira.user_request"],
            )
            return
        else:
            # Not in correct context - auto-setup
            print(f"\n⚠️  Not in the correct context for issue {resolved_issue_key}")
            for reason in preflight_result.failure_reasons:
                print(f"   - {reason}")

            if perform_auto_setup(
                resolved_issue_key,
                "create-jira-subtask",
                user_request=resolved_user_request,
                additional_params={"parent_key": resolved_parent_key} if resolved_parent_key else None,
            ):
                print("\n" + "=" * 80)
                print("Please continue the workflow in the new VS Code window.")
                print("=" * 80)
                return
            else:
                sys.exit(1)

    # No issue key - need parent_key to create placeholder
    if not resolved_parent_key:
        print("ERROR: --parent-key is required to create a placeholder subtask.")
        print("\nUsage:")
        print("  agdt-initiate-create-jira-subtask-workflow --parent-key DFLY-1234")
        sys.exit(1)

    # Extract project key from parent key
    project_key = resolved_parent_key.split("-")[0] if resolved_parent_key else "DFLY"

    # Create placeholder and set up worktree
    success, created_issue_key = create_placeholder_and_setup_worktree(
        project_key=project_key,
        issue_type="Sub-task",
        parent_key=resolved_parent_key,
        workflow_name="create-jira-subtask",
        user_request=resolved_user_request,
        additional_params={"parent_key": resolved_parent_key},
    )

    if success:
        print("\n" + "=" * 80)
        print("Please continue the workflow in the new VS Code window.")
        print("=" * 80)
    else:
        sys.exit(1)


def initiate_update_jira_issue_workflow(
    issue_key: Optional[str] = None,
    user_request: Optional[str] = None,
    _argv: Optional[List[str]] = None,
) -> None:
    """
    Initiate the update-jira-issue workflow.

    If not in the correct worktree/branch context, automatically creates
    a worktree, installs agentic-devtools, and opens VS Code.

    Usage:
        # Initial call - sets up worktree if needed:
        agdt-initiate-update-jira-issue-workflow --issue-key DFLY-1234 --user-request "I want to update..."

        # Continuation call in new VS Code window:
        agdt-initiate-update-jira-issue-workflow --issue-key DFLY-1234 --user-request "..."

    Args:
        issue_key: Jira issue key (e.g., DFLY-1234). If not provided, uses jira.issue_key from state.
        user_request: User's explanation of the updates they want. The AI agent will use this
            to determine what fields to update and how.
        _argv: Command line arguments (for testing). Pass [] to skip CLI parsing.

    Optional state:
    - jira.user_request: User's explanation of what they want to update
    - jira.summary: New summary (AI-generated from user_request)
    - jira.description: New description (AI-generated from user_request)
    - jira.comment: Comment to add
    """
    # Clear all previous state to ensure fresh workflow start
    clear_state_for_workflow_initiation()

    import argparse

    from ...state import get_value, set_value
    from .preflight import check_worktree_and_branch, perform_auto_setup

    # Parse CLI arguments if not called programmatically
    if issue_key is None and user_request is None:
        parser = argparse.ArgumentParser(description="Initiate the update-jira-issue workflow")
        parser.add_argument(
            "--issue-key",
            dest="issue_key",
            help="Jira issue key (e.g., DFLY-1234). If not provided, uses jira.issue_key from state.",
        )
        parser.add_argument(
            "--user-request",
            "-u",
            dest="user_request",
            help="Your explanation of what you want to update. AI will determine the changes to make.",
        )
        args = parser.parse_args(_argv)
        issue_key = args.issue_key
        user_request = args.user_request

    # If issue_key provided via CLI, set it in state
    if issue_key:
        set_value("jira.issue_key", issue_key)

    # If user_request provided via CLI, set it in state
    if user_request:  # pragma: no cover
        set_value("jira.user_request", user_request)

    # Get resolved values
    resolved_issue_key = get_value("jira.issue_key")
    resolved_user_request = get_value("jira.user_request")

    if not resolved_issue_key:
        print("ERROR: --issue-key is required.")
        print("\nUsage:")
        print("  agdt-initiate-update-jira-issue-workflow --issue-key DFLY-1234")
        sys.exit(1)

    # Check if we're in the correct context
    preflight_result = check_worktree_and_branch(resolved_issue_key)

    if not preflight_result.passed:
        print(f"\n⚠️  Not in the correct context for issue {resolved_issue_key}")
        for reason in preflight_result.failure_reasons:
            print(f"   - {reason}")

        # Automatically set up the environment
        if perform_auto_setup(resolved_issue_key, "update-jira-issue", user_request=resolved_user_request):
            print("\n" + "=" * 80)
            print("Please continue the workflow in the new VS Code window.")
            print("=" * 80)
            return
        else:
            sys.exit(1)

    # We're in the correct context - proceed with the workflow
    initiate_workflow(
        workflow_name="update-jira-issue",
        required_state_keys=["jira.issue_key"],
        optional_state_keys=["jira.summary", "jira.description", "jira.comment", "jira.user_request"],
    )


def initiate_apply_pull_request_review_suggestions_workflow(
    pull_request_id: Optional[str] = None,
    issue_key: Optional[str] = None,
    _argv: Optional[List[str]] = None,
) -> None:
    """
    Initiate the apply-pull-request-review-suggestions workflow.

    If not in the correct worktree/branch context, automatically creates
    a worktree, installs agentic-devtools, and opens VS Code.

    Usage:
        agdt-initiate-apply-pr-suggestions-workflow --pull-request-id 12345
        agdt-initiate-apply-pr-suggestions-workflow --pull-request-id 12345 --issue-key DFLY-1234

    Args:
        pull_request_id: ID of the pull request with suggestions to apply.
            If not provided, uses pull_request_id from state.
        issue_key: Jira issue key for context and worktree setup.
            If not provided, attempts to derive from PR source branch.
        _argv: Command line arguments (for testing). Pass [] to skip CLI parsing.

    Optional state:
    - jira.issue_key: Jira issue key for context
    """
    # Clear all previous state to ensure fresh workflow start
    clear_state_for_workflow_initiation()

    import argparse

    from ...state import get_value, set_value
    from .preflight import check_worktree_and_branch, perform_auto_setup

    # Parse CLI arguments if not called programmatically
    if pull_request_id is None and issue_key is None:
        parser = argparse.ArgumentParser(description="Initiate the apply-pull-request-review-suggestions workflow")
        parser.add_argument(
            "--pull-request-id",
            dest="pull_request_id",
            help="ID of the pull request with suggestions to apply. If not provided, uses pull_request_id from state.",
        )
        parser.add_argument(
            "--issue-key",
            "-i",
            dest="issue_key",
            help="Jira issue key for context. If not provided, derives from PR source branch.",
        )
        args = parser.parse_args(_argv)
        pull_request_id = args.pull_request_id
        issue_key = args.issue_key

    # If pull_request_id provided via CLI, set it in state
    if pull_request_id:  # pragma: no cover
        set_value("pull_request_id", pull_request_id)

    # If issue_key provided via CLI, set it in state
    if issue_key:  # pragma: no cover
        set_value("jira.issue_key", issue_key)

    # Get resolved values from state
    resolved_pr_id = get_value("pull_request_id")
    resolved_issue_key = get_value("jira.issue_key")

    # If we don't have an issue key, try to derive it from the PR
    if not resolved_issue_key and resolved_pr_id:
        from ..azure_devops.commands import _extract_issue_key_from_branch

        pr_details = get_value("pr_details")
        if pr_details and "sourceRefName" in pr_details:
            source_branch = pr_details["sourceRefName"].replace("refs/heads/", "")
            resolved_issue_key = _extract_issue_key_from_branch(source_branch)
            if resolved_issue_key:
                set_value("jira.issue_key", resolved_issue_key)

    # Check if we're in the correct worktree/branch context
    if resolved_issue_key:
        preflight_result = check_worktree_and_branch(resolved_issue_key)

        if not preflight_result.passed:
            print(f"\n⚠️  Not in the correct context for issue {resolved_issue_key}")
            for reason in preflight_result.failure_reasons:
                print(f"   - {reason}")

            # Automatically set up the environment
            if perform_auto_setup(
                resolved_issue_key,
                "apply-pull-request-review-suggestions",
                additional_params={"pull_request_id": resolved_pr_id} if resolved_pr_id else None,
            ):
                print("\n" + "=" * 80)
                print("Please continue the workflow in the new VS Code window.")
                print("=" * 80)
                return
            else:
                sys.exit(1)  # pragma: no cover

    initiate_workflow(
        workflow_name="apply-pull-request-review-suggestions",
        required_state_keys=["pull_request_id"],
        optional_state_keys=["jira.issue_key"],
    )


# =============================================================================
# Checklist Commands
# =============================================================================


def create_checklist_cmd() -> None:
    """
    Create a new implementation checklist for the current workflow.

    Usage: agdt-create-checklist [items]
           agdt-create-checklist "1. First task|2. Second task|3. Third task"

    Items can be provided as:
    - CLI argument with | delimiter
    - From state key 'checklist_items' (newline-separated)

    Creates checklist and triggers CHECKLIST_CREATED event to advance workflow.
    """
    import argparse

    from ...state import get_value, get_workflow_state, is_workflow_active
    from .checklist import Checklist, ChecklistItem, get_checklist, save_checklist
    from .manager import WorkflowEvent, notify_workflow_event

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Create an implementation checklist for the current workflow.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agdt-create-checklist "Task 1|Task 2|Task 3"
  agdt-set checklist_items "1. First task
  2. Second task"
  agdt-create-checklist
        """,
    )
    parser.add_argument(
        "items",
        nargs="?",
        type=str,
        help="Checklist items (| or newline separated). Can also use state key 'checklist_items'.",
    )
    args = parser.parse_args()

    # Verify we're in a workflow that supports checklists
    if not is_workflow_active("work-on-jira-issue"):
        print("ERROR: Checklist creation requires an active work-on-jira-issue workflow.", file=sys.stderr)
        sys.exit(1)

    workflow = get_workflow_state()
    if not workflow:  # pragma: no cover
        print("ERROR: Could not get workflow state.", file=sys.stderr)
        sys.exit(1)

    current_step = workflow.get("step", "")
    if current_step != "checklist-creation":
        # Also allow if there's already a checklist (updating)
        existing = get_checklist()
        if not existing:
            print(
                f"WARNING: Current step is '{current_step}', not 'checklist-creation'. Creating checklist anyway.",
                file=sys.stderr,
            )

    # Get items from argument or state
    items_text: Optional[str] = args.items or get_value("checklist_items")

    if not items_text:
        print("ERROR: No checklist items provided.", file=sys.stderr)
        print("\nUsage:", file=sys.stderr)
        print('  agdt-create-checklist "1. First task|2. Second task"', file=sys.stderr)
        print("  OR", file=sys.stderr)
        print('  agdt-set checklist_items "1. First task', file=sys.stderr)
        print('  2. Second task"', file=sys.stderr)
        print("  agdt-create-checklist", file=sys.stderr)
        sys.exit(1)

    # Parse items (support both | delimiter and newlines)
    raw_items = items_text.replace("|", "\n").split("\n")
    items = []
    for line in raw_items:
        line = line.strip()
        if not line:  # pragma: no cover
            continue
        # Remove leading numbers if present (e.g., "1. Task" -> "Task")
        import re

        cleaned = re.sub(r"^\d+\.\s*", "", line)
        if cleaned:
            items.append(cleaned)

    if not items:  # pragma: no cover
        print("ERROR: No valid checklist items found.", file=sys.stderr)
        sys.exit(1)

    # Create checklist
    checklist_items = [ChecklistItem(id=i + 1, text=text) for i, text in enumerate(items)]
    checklist = Checklist(items=checklist_items, modified_by_agent=False)
    save_checklist(checklist)

    # Output checklist
    print("\n" + "=" * 60)
    print("CHECKLIST CREATED")
    print("=" * 60)
    print(f"\n{len(items)} items:")
    print()
    print(checklist.render_markdown())
    print()
    print("=" * 60)

    # Trigger workflow event to advance to implementation
    result = notify_workflow_event(WorkflowEvent.CHECKLIST_CREATED)
    if result.triggered:
        if result.immediate_advance:
            # Prompt was already rendered by notify_workflow_event
            pass
        else:
            print("\n✓ Workflow transition triggered - waiting for background tasks.")
            # Auto-show the next workflow prompt
            from .manager import get_next_workflow_prompt_cmd

            get_next_workflow_prompt_cmd()
    else:
        print("\nNote: Workflow was not automatically advanced.")


def update_checklist_cmd() -> None:
    """
    Update the implementation checklist.

    Usage: agdt-update-checklist [options]

    Options:
        --add "New task"      Add a new item
        --remove "1,2"        Remove items by ID
        --complete "1,2,3"    Mark items as complete
        --revert "1,2"        Revert items to incomplete
        --edit "1:New text"   Edit an item's text

    Examples:
        agdt-update-checklist --add "Fix discovered bug"
        agdt-update-checklist --complete "1,2"
        agdt-update-checklist --revert "3"
        agdt-update-checklist --remove "5"
        agdt-update-checklist --edit "2:Updated task description"
    """
    import argparse

    from ...state import is_workflow_active
    from .checklist import get_checklist, parse_completed_items_arg, save_checklist
    from .manager import WorkflowEvent, notify_workflow_event

    # Parse arguments with argparse
    parser = argparse.ArgumentParser(
        description="Update the implementation checklist.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--add", type=str, help="Add a new item to the checklist")
    parser.add_argument("--remove", type=str, help="Remove items by ID (comma-separated)")
    parser.add_argument("--complete", type=str, help="Mark items as complete (comma-separated IDs)")
    parser.add_argument("--revert", type=str, help="Revert items to incomplete (comma-separated IDs)")
    parser.add_argument("--edit", type=str, help="Edit an item (format: 'ID:New text')")
    args = parser.parse_args()

    if not is_workflow_active("work-on-jira-issue"):
        print("ERROR: Checklist update requires an active work-on-jira-issue workflow.", file=sys.stderr)
        sys.exit(1)

    checklist = get_checklist()
    if not checklist:
        print("ERROR: No checklist exists. Create one first with agdt-create-checklist.", file=sys.stderr)
        sys.exit(1)

    # Check if any operation was specified
    if not any([args.add, args.remove, args.complete, args.revert, args.edit]):
        print("ERROR: No operation specified.", file=sys.stderr)
        print("\nUsage:", file=sys.stderr)
        print('  agdt-update-checklist --add "New task"', file=sys.stderr)
        print('  agdt-update-checklist --complete "1,2,3"', file=sys.stderr)
        print('  agdt-update-checklist --revert "1"', file=sys.stderr)
        print('  agdt-update-checklist --remove "5"', file=sys.stderr)
        print('  agdt-update-checklist --edit "2:Updated text"', file=sys.stderr)
        sys.exit(1)

    modified = False

    # Process --add
    if args.add:
        item = checklist.add_item(args.add)
        print(f"✓ Added item {item.id}: {item.text}")
        modified = True

    # Process --remove
    if args.remove:
        ids = parse_completed_items_arg(args.remove)
        for item_id in ids:
            if checklist.remove_item(item_id):
                print(f"✓ Removed item {item_id}")
            else:
                print(f"⚠ Item {item_id} not found")
        modified = True

    # Process --complete
    if args.complete:
        ids = parse_completed_items_arg(args.complete)
        marked = checklist.mark_completed(ids)
        for item_id in marked:
            print(f"✓ Marked item {item_id} complete")
        not_marked = set(ids) - set(marked)
        for item_id in not_marked:  # pragma: no cover
            print(f"⚠ Item {item_id} not found or already complete")
        modified = True

    # Process --revert
    if args.revert:
        ids = parse_completed_items_arg(args.revert)
        for item_id in ids:
            item = checklist.get_item(item_id)
            if item and item.completed:
                item.completed = False
                print(f"✓ Reverted item {item_id} to incomplete")
            elif item:
                print(f"⚠ Item {item_id} already incomplete")
            else:
                print(f"⚠ Item {item_id} not found")
        modified = True

    # Process --edit
    if args.edit:
        edit_spec = args.edit
        if ":" not in edit_spec:
            print(f'⚠ Invalid edit format: {edit_spec}. Use: --edit "1:New text"', file=sys.stderr)
        else:
            item_id_str, new_text = edit_spec.split(":", 1)
            try:
                item_id = int(item_id_str.strip())
                if checklist.update_item(item_id, new_text.strip()):
                    print(f"✓ Updated item {item_id}")
                else:
                    print(f"⚠ Item {item_id} not found")
                modified = True
            except ValueError:
                print(f"⚠ Invalid item ID: {item_id_str}", file=sys.stderr)

    if modified:
        save_checklist(checklist)
        print("\n" + "=" * 40)
        print("Updated checklist:")
        print(checklist.render_markdown())

        # Check if all items are now complete
        if checklist.all_complete():
            print("\n✓ All items complete!")
            result = notify_workflow_event(WorkflowEvent.CHECKLIST_COMPLETE)
            if result.triggered and not result.immediate_advance:
                # Has pending tasks to wait for - tell user to wait
                print("✓ Workflow transition triggered - waiting for background tasks.")
                print("   Run `agdt-get-next-workflow-prompt` to check status.")
            # If immediate_advance is True, the prompt was already rendered by notify_workflow_event


def show_checklist_cmd() -> None:
    """
    Display the current implementation checklist.

    Usage: agdt-show-checklist
    """
    from ...state import is_workflow_active
    from .checklist import get_checklist

    if not is_workflow_active("work-on-jira-issue"):
        print("No active work-on-jira-issue workflow.", file=sys.stderr)
        sys.exit(1)

    checklist = get_checklist()
    if not checklist:
        print("No checklist exists for current workflow.")
        print("\nCreate one with: agdt-create-checklist")
        return

    completed, total = checklist.completion_status()
    print("\n" + "=" * 50)
    print(f"IMPLEMENTATION CHECKLIST ({completed}/{total} complete)")
    print("=" * 50)
    print()
    print(checklist.render_markdown())
    print()

    if checklist.all_complete():
        print("✅ All items complete!")
    else:
        print(f"📋 {total - completed} item(s) remaining")


def setup_worktree_background_cmd(_argv: Optional[List[str]] = None) -> None:
    """
    Background task command to perform worktree setup.

    This command is called by the background task system and should not
    be invoked directly by users.

    Usage: agdt-setup-worktree-background --issue-key DFLY-1234 [options]

    Args:
        _argv: Command line arguments (for testing). Pass [] to skip CLI parsing.
    """
    import argparse
    import json

    from .worktree_setup import setup_worktree_in_background_sync

    parser = argparse.ArgumentParser(description="Background worktree setup (internal)")
    parser.add_argument(
        "--issue-key",
        required=True,
        dest="issue_key",
        help="Jira issue key (e.g., DFLY-1234)",
    )
    parser.add_argument(
        "--branch-prefix",
        default="feature",
        dest="branch_prefix",
        help="Branch prefix (default: feature)",
    )
    parser.add_argument(
        "--workflow-name",
        default="work-on-jira-issue",
        dest="workflow_name",
        help="Workflow name for continuation prompt",
    )
    parser.add_argument(
        "--user-request",
        default=None,
        dest="user_request",
        help="User's request explanation",
    )
    parser.add_argument(
        "--additional-params",
        default=None,
        dest="additional_params",
        help="Additional parameters as JSON string",
    )

    args = parser.parse_args(_argv)

    additional_params = None
    if args.additional_params:
        try:
            additional_params = json.loads(args.additional_params)
        except json.JSONDecodeError:
            print(f"Warning: Could not parse additional-params JSON: {args.additional_params}", file=sys.stderr)

    setup_worktree_in_background_sync(
        issue_key=args.issue_key,
        branch_prefix=args.branch_prefix,
        workflow_name=args.workflow_name,
        user_request=args.user_request,
        additional_params=additional_params,
    )
