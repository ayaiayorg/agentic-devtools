"""
CLI command entry points for git workflows.

These are the functions registered as console scripts in pyproject.toml.
"""

import argparse
import sys

from ...state import get_value, is_dry_run, read_modify_write_state
from .commit_body import assemble_message, extract_title, read_commit_body
from .commit_intent import resolve_commit_intent
from .core import (
    STATE_COMMIT_MESSAGE,
    STATE_COMMIT_MESSAGE_TITLE,
    STATE_OVERWRITE_COMMIT_MESSAGE_TITLE,
    STATE_SKIP_PUSH,
    STATE_SKIP_REBASE,
    STATE_SKIP_STAGE,
    get_bool_state,
    get_commit_message,
    run_git,
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


def _get_issue_key_from_state() -> str | None:
    """Get the current issue key from state or workflow context.

    Resolution priority:
    1. Top-level ``issue_key`` (provider-agnostic).
    2. ``jira.issue_key`` (legacy Jira-specific key).
    3. ``jira_issue_key`` from the active workflow context.
    """
    # Check top-level issue_key first (provider-agnostic).
    # Accept str (non-empty after strip) and plain int (excluding bool,
    # which is a subclass of int); ignore dict/list/bool so resolution
    # falls through to jira.issue_key / workflow context.
    issue_key = get_value("issue_key")
    if type(issue_key) is int:  # noqa: E721 – exclude bool
        return str(issue_key)
    if isinstance(issue_key, str):
        stripped = issue_key.strip()
        if stripped:
            return stripped

    # Fall back to jira.issue_key
    jira_issue_key = get_value("jira.issue_key")
    if isinstance(jira_issue_key, str):
        stripped_jira = jira_issue_key.strip()
        if stripped_jira:
            return stripped_jira
    elif jira_issue_key:
        return str(jira_issue_key)

    # Check workflow context
    workflow = get_value("workflow")
    if workflow and isinstance(workflow, dict):
        context = workflow.get("context", {})
        return context.get("jira_issue_key")

    return None


def _mark_checklist_items_completed(item_ids: list[int]) -> None:
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
        if result.triggered and not result.immediate_advance:  # pragma: no cover
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
        print("\nPlease resolve conflicts manually and then re-run agdt-git-save-work.")
        sys.exit(1)

    # Other error
    print(f"\nWarning: {result.message}")  # pragma: no cover
    print("Continuing without rebase...")  # pragma: no cover
    return False  # No rebase occurred  # pragma: no cover


def _extract_commit_parts(message: str) -> tuple[str, str]:
    """Extract title and body from a commit message.

    The title is the first line. The body is everything after the first
    line with one leading blank separator line stripped (if present).

    Args:
        message: Full commit message string.

    Returns:
        (title, body) where body is "" if the message is title-only.
    """
    if "\n" not in message:
        return (message, "")

    title, remainder = message.split("\n", 1)

    # Strip one leading blank line separator if present
    if remainder.startswith("\n"):
        body = remainder[1:]
    else:
        body = remainder

    return (title, body)


def _persist_effective_commit_message(dry_run: bool) -> None:
    """Persist the effective commit message and its parts to state after commit/amend.

    Reads back the last commit message from git and stores it in state
    for use by PR template resolution and downstream agent reuse.

    Writes 3 keys:
    - ``git.last_commit_title``: title (first line) under git namespace
    - ``git.last_commit_message``: full commit message with trailing newline(s) stripped
    - ``git.last_commit_body``: body (everything after title, separator stripped)

    Args:
        dry_run: If True, skip persistence.
    """
    if dry_run:
        return

    result = run_git("log", "-1", "--format=%B", check=False)
    if result.returncode == 0 and result.stdout.strip():
        message = result.stdout.rstrip("\n")
        title, body = _extract_commit_parts(message)
        with read_modify_write_state() as state:
            git_state = state.get("git")
            if not isinstance(git_state, dict):
                git_state = {}
                state["git"] = git_state
            git_state["last_commit_message"] = message
            git_state["last_commit_title"] = title
            git_state["last_commit_body"] = body


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
        --dry-run: Preview operations without executing
        --skip-stage: Skip the staging step
        --skip-push: Skip the push step

    Example:
        agdt-set commit_message "feat([#42](https://github.com/ayaiayorg/agentic-devtools/issues/42)): add feature"
        agdt-git-save-work
        agdt-git-save-work --completed "1,2"
        agdt-git-save-work --skip-rebase
        agdt-git-save-work --dry-run
        agdt-git-save-work --skip-stage --skip-push
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
        help=(
            "When used alone: full commit message (legacy mode, overrides state). "
            "When used with --commit-message-title: provides the body text only "
            "(the title comes from --commit-message-title)."
        ),
    )
    parser.add_argument(
        "--commit-message-title",
        type=str,
        help="Title for a new commit (errors if branch already has commits ahead)",
    )
    parser.add_argument(
        "--overwrite-commit-message-title",
        type=str,
        help="Replace the title of an existing commit (errors if no commits ahead; preserves body)",
    )
    parser.add_argument(
        "--skip-rebase",
        action="store_true",
        help="Skip the fetch/rebase onto main step",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview operations without executing",
    )
    parser.add_argument(
        "--skip-stage",
        action="store_true",
        help="Skip the staging step",
    )
    parser.add_argument(
        "--skip-push",
        action="store_true",
        help="Skip the push step",
    )
    args, _ = parser.parse_known_args()

    raw_state_commit_message_title = get_value(STATE_COMMIT_MESSAGE_TITLE)
    state_commit_message_title = (
        str(raw_state_commit_message_title) if raw_state_commit_message_title is not None else None
    )
    raw_state_overwrite_commit_message_title = get_value(STATE_OVERWRITE_COMMIT_MESSAGE_TITLE)
    state_overwrite_commit_message_title = (
        str(raw_state_overwrite_commit_message_title) if raw_state_overwrite_commit_message_title is not None else None
    )

    effective_overwrite_title = (
        getattr(args, "overwrite_commit_message_title", None)
        if getattr(args, "overwrite_commit_message_title", None) is not None
        else state_overwrite_commit_message_title
    )

    # Resolve commit message via intent system
    # First, get the raw commit_message source (CLI > template > state)
    # Note: we use get_value() instead of get_commit_message() here because the
    # intent system handles the "no message" case gracefully when title params are used.
    if args.commit_message is not None:  # pragma: no cover
        state_commit_message = args.commit_message
    elif effective_overwrite_title is not None:
        state_commit_message = None
    else:
        from .commit_template import resolve_commit_message_from_template  # noqa: PLC0415

        template_message = resolve_commit_message_from_template()
        if template_message is not None:
            state_commit_message = template_message
        else:
            raw = get_value(STATE_COMMIT_MESSAGE)
            state_commit_message = str(raw) if raw else None

    create_title_source = (
        "--commit-message-title"
        if getattr(args, "commit_message_title", None) is not None
        else "commit_message_title state key"
    )
    overwrite_title_source = (
        "--overwrite-commit-message-title"
        if getattr(args, "overwrite_commit_message_title", None) is not None
        else "overwrite_commit_message_title state key"
    )

    # Resolve intent (handles --commit-message-title, --overwrite-commit-message-title)
    intent = resolve_commit_intent(
        cli_commit_message_title=getattr(args, "commit_message_title", None),
        cli_overwrite_commit_message_title=getattr(args, "overwrite_commit_message_title", None),
        cli_commit_message=args.commit_message if args.commit_message is not None else None,
        state_commit_message_title=state_commit_message_title,
        state_overwrite_commit_message_title=state_overwrite_commit_message_title,
        state_commit_message=state_commit_message,
    )

    # Get completed items (CLI arg overrides state)
    completed_items = args.completed or get_value("completed_items")

    dry_run = args.dry_run or is_dry_run()
    skip_stage = args.skip_stage or get_bool_state(STATE_SKIP_STAGE)
    skip_rebase = args.skip_rebase or get_bool_state(STATE_SKIP_REBASE)
    skip_push = args.skip_push or get_bool_state(STATE_SKIP_PUSH)

    # Determine if we should amend or create new commit
    issue_key = _get_issue_key_from_state()
    should_amend = should_amend_instead_of_commit(issue_key)

    # Validate intent against branch state
    if intent.mode == "create" and should_amend:
        print(
            f"Error: {create_title_source} is for new commits, but branch already has "
            "commits ahead. Use --overwrite-commit-message-title (or overwrite_commit_message_title state key) "
            "to amend the existing title.",
            file=sys.stderr,
        )
        sys.exit(1)
    if intent.mode == "overwrite" and not should_amend:
        print(
            f"Error: {overwrite_title_source} requires an existing commit ahead, "
            "but no commits are ahead of main. Use --commit-message-title (or commit_message_title state key) "
            "for new commits.",
            file=sys.stderr,
        )
        sys.exit(1)

    # For overwrite mode, compose final message with preserved body from existing commit
    if intent.mode == "overwrite":
        assert intent.title is not None  # guaranteed by resolve_commit_intent for overwrite mode
        # Get the existing commit message to extract its body
        result = run_git("log", "-1", "--format=%B")
        existing_message = result.stdout or ""
        if existing_message.endswith("\n"):
            existing_message = existing_message[:-1]
        existing_lines = existing_message.split("\n", 1)
        old_title = existing_lines[0]
        existing_body = existing_lines[1] if len(existing_lines) > 1 else ""

        if existing_body:
            message = f"{intent.title}\n{existing_body}"
        else:
            message = intent.title
    else:
        message = intent.full_message

    # Apply commit-body.md injection for non-overwrite modes (overwrite preserves existing body)
    if intent.mode != "overwrite":
        body_result = read_commit_body()
        if body_result.error:
            print(f"Error: {body_result.error}", file=sys.stderr)
            sys.exit(1)
        if body_result.body.strip():
            title = extract_title(message)
            if message.strip() != title:
                print(
                    "Note: commit-body.md is present; replacing inline commit_message body/footer with file content.",
                    file=sys.stderr,
                )
            message = assemble_message(title, body_result.body)

    # Step 1: Stage changes
    if not skip_stage:
        stage_changes(dry_run)
    else:
        print("Skipping stage (skip_stage=true)")

    # Step 2: Commit or amend
    if should_amend:
        print(f"Detected existing commit for issue {issue_key or 'current branch'} - will amend")
        if intent.mode == "overwrite":
            amend_commit(message, dry_run, old_title=old_title)
        else:
            amend_commit(message, dry_run)
    else:
        print("Creating new commit...")
        create_commit(message, dry_run)

    # Persist effective commit message to state for PR template resolution
    _persist_effective_commit_message(dry_run)

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
    else:
        # Dry-run: report the push that would occur
        if needs_force_push:
            force_push(dry_run=True)
        else:
            publish_branch(dry_run=True)

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

    This is the explicit amend workflow (use agdt-git-save-work for smart detection):
    1. Stage all changes (git add .)
    2. Amend the existing commit with updated message
    3. Force push with lease

    Note: This function is intended for internal/background use and is not
    registered as a public CLI entry point.

    State keys:
        commit_message (required): The commit message (multiline supported)
        dry_run (optional): If true, show what would happen without executing
        skip_stage (optional): If true, skip the staging step
        skip_push (optional): If true, skip the push step

    CLI args:
        --completed "1,2,3": Mark checklist items as completed
        --commit-message "msg": Override commit message from state
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
    if args.completed and not dry_run:  # pragma: no cover
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

agdt-git-sync is a more descriptive name for the full workflow:
1. Fetch latest from origin/main
2. Rebase onto main if behind
3. Stage, commit (or amend), push

Use this when the name "sync" better describes your intent.
"""
