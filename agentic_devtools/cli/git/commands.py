"""
CLI command entry points for git workflows.

These are the functions registered as console scripts in pyproject.toml.
"""

import argparse
import sys
from typing import List, Optional

from ...state import get_value, is_dry_run
from .core import (
    STATE_SKIP_PUSH,
    STATE_SKIP_REBASE,
    STATE_SKIP_STAGE,
    get_bool_state,
    get_commit_message,
)
from .operations import (
    amend_commit,
    create_commit,
    fetch_main,
    force_push,
    publish_branch,
    push,
    rebase_onto_main,
    should_amend_instead_of_commit,
    stage_changes,
)


def _get_issue_key_from_state() -> Optional[str]:
    """Get the current Jira issue key from state or workflow context."""
    # Check direct state first
    issue_key = get_value("jira.issue_key")
    if issue_key:
        return str(issue_key)

    # Check workflow context
    workflow = get_value("workflow")
    if workflow and isinstance(workflow, dict):
        context = workflow.get("context", {})
        return context.get("jira_issue_key")

    return None


def _mark_checklist_items_completed(item_ids: List[int]) -> None:
    """Mark checklist items as completed and check for workflow advancement."""
    if not item_ids:
        return

    try:
        from ..workflows.checklist import get_checklist, mark_items_completed

        checklist = get_checklist()
        if not checklist:
            print(f"Note: No checklist found, ignoring --completed {item_ids}")
            return

        checklist, marked = mark_items_completed(item_ids)
        if marked:
            print(f"Marked checklist items as completed: {marked}")

        # Check if all items are now complete
        if checklist.all_complete():
            print("\n✅ All checklist items complete!")
            _trigger_implementation_review()

    except ImportError:  # pragma: no cover
        pass  # Checklist module not available
    except ValueError as e:  # pragma: no cover
        print(f"Warning: Could not update checklist: {e}")


def _trigger_implementation_review() -> None:
    """Trigger the implementation review sub-step."""
    try:
        from ..workflows.manager import WorkflowEvent, notify_workflow_event

        # Notify the workflow manager that checklist is complete
        result = notify_workflow_event(WorkflowEvent.CHECKLIST_COMPLETE)
        if result.triggered and not result.immediate_advance:
            print("Implementation review will be triggered on next prompt request.")
        # If immediate_advance is True, the prompt was already rendered

    except ImportError:  # pragma: no cover
        pass


def _sync_with_main(dry_run: bool, skip_rebase: bool) -> bool:
    """
    Fetch latest from main and rebase onto it if needed.

    Args:
        dry_run: If True, only print what would happen
        skip_rebase: If True, skip the fetch/rebase step

    Returns:
        True if a rebase occurred (history was rewritten), False otherwise.
        This is used to determine if force push is needed.
    """
    if skip_rebase:
        print("Skipping rebase onto main (skip_rebase=true)")
        return False  # No rebase occurred

    # Step 1: Fetch latest from main
    if not fetch_main(dry_run=dry_run):
        print("Warning: Could not fetch from origin/main, continuing without rebase...")
        return False  # No rebase occurred

    # Step 2: Rebase onto main if needed
    result = rebase_onto_main(dry_run=dry_run)

    if result.is_success:
        return result.was_rebased  # True if history was rewritten

    if result.needs_manual_resolution:  # pragma: no cover
        print("\n" + "=" * 60)
        print("⚠️  REBASE CONFLICTS DETECTED")
        print("=" * 60)
        print(result.message)
        print("=" * 60)
        print("\nPlease resolve conflicts manually and then re-run dfly-git-save-work.")
        sys.exit(1)

    # Other error
    print(f"\nWarning: {result.message}")  # pragma: no cover
    print("Continuing without rebase...")  # pragma: no cover
    return False  # No rebase occurred  # pragma: no cover


def commit_cmd() -> None:
    """
    Save work: stage, commit/amend, sync with main, and push.

    Full workflow:
    1. Stage all changes (git add .)
    2. Create commit or amend existing (auto-detected)
    3. Fetch latest from origin/main
    4. Rebase onto main if behind (auto-aborts on conflict with instructions)
    5. Push/force-push branch

    Automatically detects whether to create a new commit or amend:
    - If branch has no commits ahead of main → new commit
    - If last commit contains the current Jira issue key → amend
    - Otherwise → new commit

    State keys:
        commit_message (required): The commit message (multiline supported)
        jira.issue_key (optional): Used to detect if we should amend
        dry_run (optional): If true, show what would happen without executing
        skip_stage (optional): If true, skip the staging step
        skip_rebase (optional): If true, skip the fetch/rebase onto main step
        skip_push (optional): If true, skip the push step

    CLI args:
        --completed "1,2,3": Mark checklist items as completed
        --skip-rebase: Skip the fetch/rebase onto main step

    Example:
        agdt-set commit_message "feature(DFLY-1234): add feature"
        agdt-git-save-work
        agdt-git-save-work --completed "1,2"
        agdt-git-save-work --skip-rebase
    """
    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="Save work: stage, commit, rebase, push")
    parser.add_argument(
        "--completed",
        type=str,
        help="Checklist item IDs to mark as completed (e.g., '1,2,3' or '1-3')",
    )
    parser.add_argument(
        "--commit-message",
        type=str,
        help="Commit message (overrides state)",
    )
    parser.add_argument(
        "--skip-rebase",
        action="store_true",
        help="Skip the fetch/rebase onto main step",
    )
    args, _ = parser.parse_known_args()

    # Get commit message (CLI arg overrides state)
    if args.commit_message:  # pragma: no cover
        message = args.commit_message
    else:
        message = get_commit_message()

    # Get completed items (CLI arg overrides state)
    completed_items = args.completed or get_value("completed_items")

    dry_run = is_dry_run()
    skip_stage = get_bool_state(STATE_SKIP_STAGE)
    skip_rebase = args.skip_rebase or get_bool_state(STATE_SKIP_REBASE)
    skip_push = get_bool_state(STATE_SKIP_PUSH)

    # Determine if we should amend or create new commit
    issue_key = _get_issue_key_from_state()
    should_amend = should_amend_instead_of_commit(issue_key)

    # Step 1: Stage changes
    if not skip_stage:
        stage_changes(dry_run)
    else:
        print("Skipping stage (skip_stage=true)")

    # Step 2: Commit or amend
    if should_amend:
        print(f"Detected existing commit for issue {issue_key or 'current branch'} - will amend")
        amend_commit(message, dry_run)
    else:
        print("Creating new commit...")
        create_commit(message, dry_run)

    # Step 3-4: Sync with main (fetch + rebase) - after commit so no unstaged changes
    rebase_occurred = _sync_with_main(dry_run, skip_rebase)

    # Step 5: Push/force-push
    # Use force push if we amended OR if rebase rewrote history
    needs_force_push = should_amend or rebase_occurred
    if skip_push:
        print("Skipping push (skip_push=true)")
    elif not dry_run:
        if needs_force_push:
            force_push(dry_run=False)
        else:
            publish_branch(dry_run=False)

    # Mark checklist items if specified
    if completed_items and not dry_run:
        from ..workflows.checklist import parse_completed_items_arg

        item_ids = parse_completed_items_arg(completed_items)
        _mark_checklist_items_completed(item_ids)

        # Clear the completed_items state after processing
        from ...state import delete_value

        delete_value("completed_items")

    if dry_run:
        print("\n[DRY RUN] No changes were made.")
    else:
        # Try to advance workflow if applicable (and no checklist triggered review)
        try:
            from ..workflows.advancement import try_advance_workflow_after_commit

            try_advance_workflow_after_commit()
        except ImportError:  # pragma: no cover
            pass


def _do_amend(message: str, dry_run: bool, skip_stage: bool) -> None:
    """Execute the amend commit workflow."""
    skip_push = get_bool_state(STATE_SKIP_PUSH)

    # Stage changes
    if not skip_stage:
        stage_changes(dry_run)
    else:
        print("Skipping stage (skip_stage=true)")

    # Amend commit
    amend_commit(message, dry_run)

    # Force push
    if skip_push:
        print("Skipping push (skip_push=true)")
    elif not dry_run:
        force_push(dry_run=False)


def amend_cmd() -> None:
    """
    Stage, amend commit, and force push.

    This is the explicit amend workflow (use dfly-git-save-work for smart detection):
    1. Stage all changes (git add .)
    2. Amend the existing commit with updated message
    3. Force push with lease

    State keys:
        commit_message (required): The commit message (multiline supported)
        dry_run (optional): If true, show what would happen without executing
        skip_stage (optional): If true, skip the staging step
        skip_push (optional): If true, skip the push step

    CLI args:
        --completed "1,2,3": Mark checklist items as completed
        --commit-message "msg": Override commit message from state

    Example:
        agdt-set commit_message "feature(DFLY-1234): add feature (updated)"
        agdt-git-amend
        agdt-git-amend --completed "1,2"
    """
    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="Git amend commit")
    parser.add_argument(
        "--completed",
        type=str,
        help="Checklist item IDs to mark as completed (e.g., '1,2,3' or '1-3')",
    )
    parser.add_argument(
        "--commit-message",
        type=str,
        help="Commit message (overrides state)",
    )
    args, _ = parser.parse_known_args()

    # Get commit message (CLI arg overrides state)
    if args.commit_message:  # pragma: no cover
        message = args.commit_message
    else:
        message = get_commit_message()

    dry_run = is_dry_run()
    skip_stage = get_bool_state(STATE_SKIP_STAGE)

    _do_amend(message, dry_run, skip_stage)

    # Mark checklist items if specified
    if args.completed and not dry_run:
        from ..workflows.checklist import parse_completed_items_arg

        item_ids = parse_completed_items_arg(args.completed)
        _mark_checklist_items_completed(item_ids)

    if dry_run:  # pragma: no cover
        print("\n[DRY RUN] No changes were made.")


def stage_cmd() -> None:
    """
    Stage all changes (git add .).

    State keys:
        dry_run (optional): If true, show what would happen without executing

    Example:
        agdt-git-stage
    """
    stage_changes(is_dry_run())


def push_cmd() -> None:
    """
    Push the current branch (for already-published branches).

    State keys:
        dry_run (optional): If true, show what would happen without executing

    Example:
        agdt-git-push
    """
    push(is_dry_run())


def force_push_cmd() -> None:
    """
    Force push with lease (git push --force-with-lease).

    State keys:
        dry_run (optional): If true, show what would happen without executing

    Example:
        agdt-git-force-push
    """
    force_push(is_dry_run())


def publish_cmd() -> None:
    """
    Publish the current branch (push with upstream tracking).

    State keys:
        dry_run (optional): If true, show what would happen without executing

    Example:
        agdt-git-publish
    """
    publish_branch(is_dry_run())


# Alias for commit_cmd - more descriptive name for the full workflow
sync_cmd = commit_cmd
"""
Alias for commit_cmd.

dfly-git-sync is a more descriptive name for the full workflow:
1. Fetch latest from origin/main
2. Rebase onto main if behind
3. Stage, commit (or amend), push

Use this when the name "sync" better describes your intent.
"""
