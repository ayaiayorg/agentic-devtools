"""
Async Git command wrappers.

Provides async versions of Git commands that run in background processes.

These async commands call the sync functions directly via run_function_in_background,
not via CLI entry points.
"""

import argparse
import sys
from typing import List, Optional

from agentic_devtools.background_tasks import run_function_in_background
from agentic_devtools.state import set_value
from agentic_devtools.task_state import print_task_tracking_info

# Module path for the sync functions
_GIT_COMMANDS_MODULE = "agentic_devtools.cli.git.commands"

# State keys
STATE_COMMIT_MESSAGE = "commit_message"


def _set_value_if_provided(key: str, value: Optional[str]) -> None:
    """Set a state value if provided (not None)."""
    if value is not None:
        set_value(key, value)


def _set_bool_value_if_true(key: str, value: bool) -> None:
    """Set a state value to 'true' if the boolean is True."""
    if value:
        set_value(key, "true")


def _create_commit_parser() -> argparse.ArgumentParser:
    """Create argument parser for save-work command."""
    parser = argparse.ArgumentParser(
        prog="agdt-git-save-work",
        description="Save work: stage, commit (or amend), rebase onto main, and push.",
        epilog="""
Examples:
  dfly-git-save-work -m "feature(DFLY-1234): add new feature"
  dfly-git-save-work --commit-message "fix: resolve issue"
  dfly-git-save-work --completed "1,2,3"
  dfly-git-save-work --skip-rebase
  dfly-set commit_message "feature(DFLY-1234): add feature"
  dfly-git-save-work

Behavior:
  - Stages all changes and commits (or amends if existing commit for issue)
  - Fetches latest from origin/main and rebases onto it (if behind)
  - Automatically aborts rebase on conflicts with manual resolution instructions
  - Pushes (or force-pushes for amends) to remote
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-m",
        "--message",
        "--commit-message",
        dest="commit_message",
        type=str,
        metavar="MESSAGE",
        help="Commit message (saved to state, multiline supported)",
    )
    parser.add_argument(
        "--completed",
        type=str,
        metavar="ITEMS",
        help="Checklist item IDs to mark as completed (e.g., '1,2,3' or '1-3')",
    )
    parser.add_argument(
        "--skip-rebase",
        action="store_true",
        help="Skip the fetch/rebase onto main step",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes",
    )
    return parser


def commit_async(
    message: Optional[str] = None,
    completed: Optional[str] = None,
    skip_rebase: bool = False,
    dry_run: bool = False,
    _argv: Optional[List[str]] = None,
) -> None:
    """
    Save work: stage, commit, rebase onto main, and push asynchronously in background.

    Full workflow:
    1. Stage all changes (git add .)
    2. Create commit or amend existing (auto-detected)
    3. Fetch latest from origin/main
    4. Rebase onto main if behind (auto-aborts on conflict with instructions)
    5. Push/force-push branch

    Args:
        message: Commit message (saved to state if provided)
        completed: Checklist items to mark completed (e.g., "1,2,3")
        skip_rebase: Skip the fetch/rebase onto main step
        dry_run: Show what would happen without making changes
        _argv: CLI arguments (for testing)

    State keys:
        commit_message (required): The commit message (multiline supported)
        dry_run (optional): If true, show what would happen without executing
        skip_stage (optional): If true, skip the staging step
        skip_push (optional): If true, skip the push step
        skip_rebase (optional): If true, skip the fetch/rebase onto main step

    Usage:
        dfly-git-save-work -m "feature(DFLY-1234): add feature"
        dfly-git-save-work --message "feature(DFLY-1234): add feature"
        dfly-git-save-work --commit-message "feature(DFLY-1234): add feature"
        dfly-git-save-work --completed "1,2,3"
        dfly-git-save-work --skip-rebase
        dfly-git-save-work --dry-run
        dfly-git-save-work --help
    """
    # Parse CLI arguments
    parser = _create_commit_parser()
    argv = _argv if _argv is not None else sys.argv[1:]
    args, _ = parser.parse_known_args(argv)

    # CLI args override function parameters
    effective_message = args.commit_message or message
    effective_completed = args.completed or completed
    effective_skip_rebase = args.skip_rebase or skip_rebase
    effective_dry_run = args.dry_run or dry_run

    # Save message to state if provided
    _set_value_if_provided(STATE_COMMIT_MESSAGE, effective_message)

    # Save completed items to state for the sync command to read
    _set_value_if_provided("completed_items", effective_completed)

    # Save skip_rebase to state if true
    _set_bool_value_if_true("skip_rebase", effective_skip_rebase)

    # Always set dry_run to avoid inheriting previous value
    set_value("dry_run", str(effective_dry_run).lower())

    task = run_function_in_background(
        _GIT_COMMANDS_MODULE,
        "commit_cmd",
        command_display_name="agdt-git-save-work",
    )
    print_task_tracking_info(task)


def amend_async(
    message: Optional[str] = None,
    _argv: Optional[List[str]] = None,
) -> None:
    """
    Stage, amend commit, and force push asynchronously in the background.

    This is the follow-up commit workflow (single-commit policy):
    1. Stage all changes (git add .)
    2. Amend the existing commit with updated message
    3. Force push with lease

    Note: This function is primarily for internal use. The dfly-git-save-work
    command now auto-detects when to amend based on branch state.

    Args:
        message: Commit message (saved to state if provided)
        _argv: CLI arguments (for testing)

    State keys:
        commit_message (required): The commit message (multiline supported)
        dry_run (optional): If true, show what would happen without executing
        skip_stage (optional): If true, skip the staging step
        skip_push (optional): If true, skip the push step

    Usage:
        dfly-git-amend -m "feature(DFLY-1234): updated message"
        dfly-git-amend --message "feature(DFLY-1234): updated message"
    """
    # Parse CLI arguments for message
    parser = argparse.ArgumentParser(prog="agdt-git-amend", add_help=False)
    parser.add_argument("-m", "--message", "--commit-message", dest="commit_message", type=str)
    argv = _argv if _argv is not None else sys.argv[1:]
    args, _ = parser.parse_known_args(argv)

    # CLI args override function parameters
    effective_message = args.commit_message or message

    # Save message to state if provided
    _set_value_if_provided(STATE_COMMIT_MESSAGE, effective_message)

    task = run_function_in_background(
        _GIT_COMMANDS_MODULE,
        "amend_cmd",
        command_display_name="agdt-git-amend",
    )
    print_task_tracking_info(task)


def stage_async() -> None:
    """
    Stage all changes asynchronously in the background.

    State keys:
        dry_run (optional): If true, show what would happen without executing

    Usage:
        dfly-git-stage
    """
    task = run_function_in_background(
        _GIT_COMMANDS_MODULE,
        "stage_cmd",
        command_display_name="agdt-git-stage",
    )
    print_task_tracking_info(task)


def push_async() -> None:
    """
    Push the current branch asynchronously in the background.

    For already-published branches.

    State keys:
        dry_run (optional): If true, show what would happen without executing

    Usage:
        dfly-git-push
    """
    task = run_function_in_background(
        _GIT_COMMANDS_MODULE,
        "push_cmd",
        command_display_name="agdt-git-push",
    )
    print_task_tracking_info(task)


def force_push_async() -> None:
    """
    Force push with lease asynchronously in the background.

    State keys:
        dry_run (optional): If true, show what would happen without executing

    Usage:
        dfly-git-force-push
    """
    task = run_function_in_background(
        _GIT_COMMANDS_MODULE,
        "force_push_cmd",
        command_display_name="agdt-git-force-push",
    )
    print_task_tracking_info(task)


def publish_async() -> None:
    """
    Publish the current branch asynchronously in the background.

    Push with upstream tracking.

    State keys:
        dry_run (optional): If true, show what would happen without executing

    Usage:
        dfly-git-publish
    """
    task = run_function_in_background(
        _GIT_COMMANDS_MODULE,
        "publish_cmd",
        command_display_name="agdt-git-publish",
    )
    print_task_tracking_info(task)


# Alias for commit_async - more descriptive name for the full workflow
sync_async = commit_async
"""
Alias for commit_async.

dfly-git-sync is a more descriptive name for the full workflow:
1. Fetch latest from origin/main
2. Rebase onto main if behind
3. Stage, commit (or amend), push

Use this when the name "sync" better describes your intent.
"""
