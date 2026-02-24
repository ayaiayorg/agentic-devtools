"""
Task monitoring commands.

CLI commands for monitoring and managing background tasks.
"""

import argparse
import sys
from datetime import datetime, timezone
from typing import List, Optional

from ...background_tasks import get_task_log_content
from ...task_state import (
    BackgroundTask,
    TaskStatus,
    cleanup_expired_tasks,
    get_background_tasks,
    get_other_incomplete_tasks,
    get_task_by_id,
)


def _get_task_id_from_args_or_state(_argv: Optional[List[str]] = None) -> str:
    """
    Get task ID from CLI args or state.

    If --id is provided, updates state with the new task_id.

    Args:
        _argv: Optional list of CLI arguments (for testing)

    Returns:
        Task ID string

    Raises:
        SystemExit: If no task ID is available
    """
    from ...state import get_value, set_value

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--id", type=str, default=None, help="Task ID to track")

    args, _ = parser.parse_known_args(_argv)

    if args.id:
        # Update state with the provided task ID
        set_value("background.task_id", args.id)
        return args.id

    task_id = get_value("background.task_id")

    if not task_id:
        print("Error: No task ID specified.")
        print('Set a task ID with: agdt-set background.task_id <task-id> or use --id "<task-id>"')
        sys.exit(1)

    return task_id


def _safe_print(text: str) -> None:
    """
    Print text safely, handling unicode encoding errors.

    On Windows with cp1252 encoding, emoji characters may fail to encode.
    This function replaces non-encodable characters with ASCII equivalents.
    """
    try:
        print(text)
    except UnicodeEncodeError:
        # Replace emoji with ASCII equivalents
        ascii_replacements = {
            "\u2705": "[OK]",  # ✅
            "\u274c": "[FAIL]",  # ❌
            "\u23f3": "[...]",  # ⏳
            "\U0001f504": "[~]",  # 🔄
            "\u2753": "[?]",  # ❓
            "\u23f0": "[TIMEOUT]",  # ⏰
            "\U0001f4cb": "[LIST]",  # 📋
            "\u2022": "-",  # •
        }
        safe_text = text
        for emoji, replacement in ascii_replacements.items():
            safe_text = safe_text.replace(emoji, replacement)
        # Final fallback: encode with replace
        print(safe_text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode())


def _format_timestamp(ts: Optional[str]) -> str:
    """Format an ISO timestamp for display."""
    if not ts:
        return "N/A"
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return ts


def _format_duration(task: BackgroundTask) -> str:
    """Calculate and format task duration."""
    if not task.start_time:
        return "Not started"

    start = datetime.fromisoformat(task.start_time)

    if task.end_time:
        end = datetime.fromisoformat(task.end_time)
    elif task.status == TaskStatus.RUNNING:
        end = datetime.now(timezone.utc)
    else:
        return "Unknown"

    duration = end - start
    total_seconds = int(duration.total_seconds())

    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def _status_indicator(status: TaskStatus) -> str:
    """Get a status indicator symbol."""
    indicators = {
        TaskStatus.PENDING: "⏳",
        TaskStatus.RUNNING: "🔄",
        TaskStatus.COMPLETED: "✅",
        TaskStatus.FAILED: "❌",
    }
    return indicators.get(status, "❓")


def list_tasks() -> None:
    """
    List all background tasks.

    Entry point: agdt-tasks
    """
    tasks = get_background_tasks()

    if not tasks:
        print("No background tasks found.")
        return

    # Sort by start_time descending (most recent first)
    sorted_tasks = sorted(
        tasks,
        key=lambda t: t.start_time or "",
        reverse=True,
    )

    print(f"\n{'ID':<36}  {'Status':<12}  {'Command':<30}  {'Duration':<10}  Created")
    print("-" * 110)

    for task in sorted_tasks:
        status_str = f"{_status_indicator(task.status)} {task.status.value}"
        command_display = task.command[:27] + "..." if len(task.command) > 30 else task.command
        duration = _format_duration(task)
        created = _format_timestamp(task.start_time)

        _safe_print(f"{task.id:<36}  {status_str:<12}  {command_display:<30}  {duration:<10}  {created}")

    print(f"\nTotal: {len(tasks)} task(s)")

    # Count by status
    status_counts = {}
    for task in tasks:
        status_counts[task.status] = status_counts.get(task.status, 0) + 1

    status_summary = ", ".join(
        f"{status.value}: {count}" for status, count in sorted(status_counts.items(), key=lambda x: x[0].value)
    )
    print(f"By status: {status_summary}")


def task_status(_argv: Optional[List[str]] = None) -> None:
    """
    Show detailed status of a specific task.

    Entry point: agdt-task-status

    Args:
        _argv: Optional list of CLI arguments (for testing)

    CLI args:
        --id: Task ID to show status for (overrides state, updates background.task_id)

    Reads task ID from state: background.task_id (if --id not provided)
    """
    task_id = _get_task_id_from_args_or_state(_argv)

    task = get_task_by_id(task_id)

    if not task:
        print(f"Error: Task '{task_id}' not found.")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"Task Details: {task.id}")
    print(f"{'=' * 60}")
    print(f"  Command:     {task.command}")
    _safe_print(f"  Status:      {_status_indicator(task.status)} {task.status.value}")
    print(f"  Started:     {_format_timestamp(task.start_time)}")
    print(f"  Completed:   {_format_timestamp(task.end_time)}")
    print(f"  Duration:    {_format_duration(task)}")

    if task.exit_code is not None:
        print(f"  Exit Code:   {task.exit_code}")

    if task.log_file:  # pragma: no cover
        print(f"  Log File:    {task.log_file}")

    if task.error_message:  # pragma: no cover
        print(f"  Error:       {task.error_message}")

    print(f"{'=' * 60}")


def task_log(_argv: Optional[List[str]] = None) -> None:
    """
    Display task log contents.

    Entry point: agdt-task-log

    Args:
        _argv: Optional list of CLI arguments (for testing)

    CLI args:
        --id: Task ID to show log for (overrides state, updates background.task_id)

    Reads task ID from state: background.task_id (if --id not provided)
    Optional state keys:
    - background.log_lines: Number of lines to show (default: all, use negative for tail)
    """
    from ...state import get_value

    task_id = _get_task_id_from_args_or_state(_argv)

    task = get_task_by_id(task_id)

    if not task:
        print(f"Error: Task '{task_id}' not found.")
        sys.exit(1)

    log_content = get_task_log_content(task_id)

    if log_content is None:  # pragma: no cover
        print(f"No log file available for task '{task_id}'.")
        if task.log_file:
            print(f"Expected log file: {task.log_file}")
        sys.exit(1)

    # Check for line limit
    lines_str = get_value("background.log_lines")
    if lines_str:
        try:
            lines_limit = int(lines_str)
            log_lines = log_content.splitlines()

            if lines_limit < 0:
                # Tail mode: show last N lines
                log_lines = log_lines[lines_limit:]
            elif lines_limit > 0:
                # Head mode: show first N lines
                log_lines = log_lines[:lines_limit]

            log_content = "\n".join(log_lines)
        except ValueError:
            pass  # Ignore invalid line count

    print(f"\n--- Log for task {task_id} ---")
    print(f"Command: {task.command}")
    _safe_print(f"Status: {_status_indicator(task.status)} {task.status.value}")
    print("-" * 50)
    print(log_content)
    print("-" * 50)


def _parse_wait_args(_argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse arguments for task_wait command.

    Args:
        _argv: Optional list of CLI arguments (for testing)

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog="agdt-task-wait",
        description="Wait for a background task to complete",
        add_help=True,
    )
    parser.add_argument("--id", type=str, default=None, help="Task ID to wait for")
    parser.add_argument(
        "--wait-interval",
        type=float,
        default=1.0,
        help="Seconds to wait between status checks (default: 1.0)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Maximum seconds since task start before timeout (default: 300)",
    )

    return parser.parse_args(_argv or [])


def _check_task_timeout(task: BackgroundTask, timeout: float) -> bool:
    """
    Check if task has exceeded timeout based on its start_time.

    Args:
        task: The background task to check
        timeout: Maximum seconds since task start

    Returns:
        True if task has timed out, False otherwise
    """
    if not task.start_time:  # pragma: no cover
        return False  # Can't determine timeout without start time

    try:
        # Parse start_time (ISO format)
        start_dt = datetime.fromisoformat(task.start_time.replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - start_dt).total_seconds()
        return elapsed > timeout
    except (ValueError, TypeError):  # pragma: no cover
        return False  # Can't determine timeout with invalid start time


def task_wait(_argv: Optional[List[str]] = None) -> None:
    """
    Wait for task completion and auto-progress workflow.

    Entry point: agdt-task-wait

    This command checks task status twice (with a configurable wait between checks):
    1. If task completed → Handles success/failure as appropriate
    2. If task still running → Tells AI agent to call agdt-task-wait again
    3. If task timed out (based on start_time) → Reports timeout

    After task completion:
    1. If task failed → Shows log with fix instructions
    2. If other incomplete most-recent-per-command tasks exist → Instructs to wait for them
    3. If any most-recent-per-command task failed → Instructs to review it
    4. If all clear → Automatically runs agdt-get-next-workflow-prompt

    Args:
        _argv: Optional list of CLI arguments (for testing)

    CLI args:
        --id: Task ID to wait for (overrides state, updates background.task_id)
        --wait-interval: Seconds to wait between checks (default: 1.0)
        --timeout: Max seconds since task start before timeout (default: 300)

    Reads task ID from state: background.task_id (if --id not provided)
    """
    import time

    from ...state import get_value, set_value

    # Parse args
    args = _parse_wait_args(_argv)

    # Handle task ID (from arg or state)
    if args.id:
        set_value("background.task_id", args.id)
        task_id = args.id
    else:
        task_id = get_value("background.task_id")
        if not task_id:
            print("Error: No task ID specified.")
            print('Set a task ID with: agdt-set background.task_id <task-id> or use --id "<task-id>"')
            sys.exit(1)

    # Allow state overrides for wait_interval and timeout
    wait_interval = args.wait_interval
    timeout = args.timeout

    wait_interval_str = get_value("background.wait_interval")
    if wait_interval_str:
        try:
            wait_interval = float(wait_interval_str)
        except ValueError:
            pass  # Keep CLI arg value

    timeout_str = get_value("background.timeout")
    if timeout_str:
        try:
            timeout = float(timeout_str)
        except ValueError:
            pass  # Keep CLI arg value

    # Get task details
    task = get_task_by_id(task_id)
    if task is None:  # pragma: no cover
        print(f"Error: Task '{task_id}' not found.")
        sys.exit(1)

    print(f"Checking task (command: {task.command}, id: {task_id})...")

    # Check 1: Is task already complete?
    if task.is_terminal():
        _handle_task_completed(task, task_id, timeout)
        return

    # Check timeout based on start_time
    if _check_task_timeout(task, timeout):  # pragma: no cover
        _handle_task_timeout(task, task_id, timeout)
        return

    # Task still running - wait and check again
    print(f"Task still running, waiting {wait_interval}s...")
    time.sleep(wait_interval)

    # Check 2: Re-fetch and check status
    task = get_task_by_id(task_id)
    if task is None:  # pragma: no cover
        print(f"Error: Task '{task_id}' disappeared during wait.")
        sys.exit(1)

    if task.is_terminal():
        _handle_task_completed(task, task_id, timeout)
        return

    # Check timeout again
    if _check_task_timeout(task, timeout):  # pragma: no cover
        _handle_task_timeout(task, task_id, timeout)
        return

    # Task still running after 2 checks - tell AI to wait again
    _handle_task_still_running(task, task_id, wait_interval)


def _handle_task_still_running(task: BackgroundTask, task_id: str, wait_interval: float) -> None:
    """Handle case where task is still running after checks."""
    elapsed = _get_task_elapsed_time(task)

    print()
    print("=" * 70)
    _safe_print("⏳ TASK STILL IN PROGRESS")
    print("=" * 70)
    _safe_print(f"\nTask: {task.command}")
    _safe_print(f"Status: {_status_indicator(task.status)} {task.status.value}")
    if elapsed is not None:
        print(f"Running for: {elapsed:.1f}s")

    _safe_print("\n📋 Next Step:")
    print("  Run agdt-task-wait again to continue waiting for completion.")
    print()
    print("Alternative actions:")
    print("  • Check status: agdt-task-status")
    print("  • View log: agdt-task-log")
    sys.exit(0)


def _handle_task_timeout(task: BackgroundTask, task_id: str, timeout: float) -> None:
    """Handle case where task has exceeded timeout."""
    elapsed = _get_task_elapsed_time(task)

    print()
    print("=" * 70)
    _safe_print("⏰ TASK TIMEOUT")
    print("=" * 70)
    _safe_print(f"\nTask: {task.command}")
    _safe_print(f"Status: {_status_indicator(task.status)} {task.status.value}")
    if elapsed is not None:
        print(f"Running for: {elapsed:.1f}s (timeout: {timeout}s)")

    _safe_print("\n📋 Next Steps:")
    print("  1. Check if task is stuck: agdt-task-log")
    print("  2. If stuck, consider canceling and retrying")
    print(f"  3. Or increase timeout: agdt-set background.timeout {int(timeout * 2)}")
    sys.exit(2)


def _get_task_elapsed_time(task: BackgroundTask) -> Optional[float]:
    """Get elapsed time in seconds since task started."""
    if not task.start_time:  # pragma: no cover
        return None
    try:
        start_dt = datetime.fromisoformat(task.start_time.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - start_dt).total_seconds()
    except (ValueError, TypeError):  # pragma: no cover
        return None


def _try_advance_pr_review_to_summary() -> bool:
    """
    Check if pull-request-review workflow should auto-advance to summary step.

    This function checks if:
    1. Current workflow is pull-request-review
    2. Current step is file-review
    3. All files have been reviewed (queue all_complete is True)

    If all conditions are met:
    - Advances workflow to summary step
    - Triggers generate_pr_summary_async() as background task
    - Sets background.task_id to the new summary task
    - Prints message instructing AI to run agdt-task-wait

    Returns:
        True if workflow was advanced and summary task started
        False if conditions not met or workflow not applicable
    """
    from ...state import get_value, get_workflow_state, set_value

    # Check if we're in pull-request-review workflow at file-review step
    workflow = get_workflow_state()
    if not workflow:
        return False

    workflow_name = workflow.get("active", "")
    current_step = workflow.get("step", "")

    if workflow_name != "pull-request-review" or current_step != "file-review":
        return False

    # Get PR ID to check queue status
    pr_id_str = get_value("pull_request_id")
    if not pr_id_str:
        return False

    try:
        pr_id = int(pr_id_str)
    except ValueError:
        return False

    # Check if all files are complete
    from ..azure_devops.file_review_commands import get_queue_status

    queue_status = get_queue_status(pr_id)
    if not queue_status.get("all_complete", False):
        return False

    # Also wait for all submissions to complete before generating summary
    if queue_status.get("submission_pending_count", 0) > 0:
        return False

    # All conditions met - advance workflow to summary step
    from ..workflows.base import set_workflow_state

    context = workflow.get("context", {})
    set_workflow_state(
        name="pull-request-review",
        status="in-progress",
        step="summary",
        context=context,
    )

    # Start summary generation as background task (without printing tracking info)
    from ...background_tasks import run_function_in_background
    from ...task_state import BackgroundTask

    _PR_SUMMARY_MODULE = "agentic_devtools.cli.azure_devops.pr_summary_commands"
    task: BackgroundTask = run_function_in_background(
        _PR_SUMMARY_MODULE,
        "generate_overarching_pr_comments_cli",
        command_display_name="agdt-generate-pr-summary",
    )

    # Update background.task_id so next agdt-task-wait tracks this task
    set_value("background.task_id", task.id)

    # Print clear, unambiguous message for AI agent
    print()
    print("=" * 70)
    _safe_print("✅ ALL FILE REVIEWS COMPLETE - AUTO-GENERATING PR SUMMARY")
    print("=" * 70)
    print()
    print("PR summary generation has been AUTOMATICALLY started in the background.")
    print(f"Task ID: {task.id}")
    print()
    print("IMPORTANT: The summary will be posted automatically. Do NOT manually")
    print("trigger dfly-generate-pr-summary - it is already running.")
    print()
    _safe_print("📋 YOUR ONLY ACTION: Run agdt-task-wait")
    print()
    print("This will wait for the summary to complete and then provide next steps.")

    return True


def _try_complete_pr_review_workflow(task: BackgroundTask) -> bool:
    """
    Check if pull-request-review workflow should complete after summary generation.

    This function checks if:
    1. Current workflow is pull-request-review
    2. Current step is summary
    3. The completed task was dfly-generate-pr-summary

    If all conditions are met:
    - Advances workflow to completion step
    - Prints completion message

    Args:
        task: The background task that just completed

    Returns:
        True if workflow was completed
        False if conditions not met or workflow not applicable
    """
    from ...state import get_workflow_state

    # Check if we're in pull-request-review workflow at summary step
    workflow = get_workflow_state()
    if not workflow:
        return False

    workflow_name = workflow.get("active", "")
    current_step = workflow.get("step", "")

    if workflow_name != "pull-request-review" or current_step != "summary":
        return False

    # Check if the completed task was the summary generation
    if task.command != "agdt-generate-pr-summary":
        return False

    # All conditions met - advance workflow to completion
    from ..workflows.base import set_workflow_state

    context = workflow.get("context", {})
    set_workflow_state(
        name="pull-request-review",
        status="completed",
        step="completion",
        context=context,
    )

    # Print completion message
    print()
    print("=" * 70)
    _safe_print("✅ PR REVIEW WORKFLOW COMPLETE")
    print("=" * 70)
    print()
    print("All file reviews have been submitted and summary comments posted.")
    print("The pull-request-review workflow has completed successfully.")
    print()
    print("NEXT STEPS:")
    print("  1. Review the PR summary comments that were posted")
    print("  2. Make a final decision on the PR:")
    print("     - To approve: agdt-approve-pull-request")
    print("     - Or provide feedback and request changes as needed")

    return True


def _handle_task_completed(task: BackgroundTask, task_id: str, timeout: float) -> None:
    """
    Handle a completed task (success or failure).

    This contains the original post-completion logic from task_wait.
    """
    from ...task_state import (
        get_failed_most_recent_per_command,
        get_incomplete_most_recent_per_command,
    )

    _safe_print(f"\nTask completed with status: {_status_indicator(task.status)} {task.status.value}")
    print(f"Duration: {_format_duration(task)}")

    if task.exit_code is not None:
        print(f"Exit code: {task.exit_code}")

    # Handle task failure - show log with fix instructions
    if task.status == TaskStatus.FAILED:
        print("\n" + "=" * 70)
        _safe_print("❌ TASK FAILED - Review log and fix the issue")
        print("=" * 70)

        if task.error_message:
            print(f"\nError: {task.error_message}")

        # Show the log
        print("\n--- Task Log ---")
        log_content = get_task_log_content(task_id)
        if log_content:
            print(log_content)
        else:
            print("(No log content available)")
        print("--- End Log ---")

        _safe_print("\n📋 Next Steps:")
        print("  1. Review the error above")
        print("  2. Fix the underlying issue")
        print(f"  3. Re-run the command: {task.command}")
        print("  4. Run agdt-task-wait again")
        sys.exit(task.exit_code if task.exit_code is not None else 1)

    # Task succeeded - now check for other tasks
    print()

    # Check for other incomplete most-recent-per-command tasks
    other_incomplete = get_incomplete_most_recent_per_command(exclude_task_id=task_id)
    if other_incomplete:
        print("=" * 70)
        _safe_print("⏳ OTHER TASKS STILL RUNNING")
        print("=" * 70)
        print(f"\n{len(other_incomplete)} other task(s) still in progress:")
        for other_task in other_incomplete:
            _safe_print(f"  • {other_task.command} (id: {other_task.id}, status: {other_task.status.value})")

        # Pick the first one to wait for
        next_task = other_incomplete[0]
        _safe_print("\n📋 Next Step:")
        print(f'  agdt-task-wait --id "{next_task.id}"')
        sys.exit(0)

    # Check for failed most-recent-per-command tasks
    # Exclude the current task's command since it just succeeded - we don't want to
    # report an older failed task for the same command
    failed_tasks = get_failed_most_recent_per_command(
        exclude_task_id=task_id,
        exclude_commands=[task.command],
    )
    if failed_tasks:
        print("=" * 70)
        _safe_print("❌ OTHER TASKS FAILED - Review and fix")
        print("=" * 70)
        print(f"\n{len(failed_tasks)} task(s) failed:")
        for failed_task in failed_tasks:
            _safe_print(f"  • {failed_task.command} (id: {failed_task.id})")

        # Pick the first one to review
        next_task = failed_tasks[0]
        _safe_print("\n📋 Next Steps:")
        print(f'  1. Review the failed task: agdt-task-log --id "{next_task.id}"')
        print("  2. Fix the underlying issue")
        print(f"  3. Re-run the command: {next_task.command}")
        sys.exit(0)

    # All tasks succeeded - check for special workflow handling
    # Check if we need to auto-advance pull-request-review workflow
    if _try_advance_pr_review_to_summary():
        # Successfully advanced and triggered summary - AI agent should run agdt-task-wait
        sys.exit(0)  # pragma: no cover

    # Check if pull-request-review workflow should complete after summary
    if _try_complete_pr_review_workflow(task):
        # Workflow completed successfully
        sys.exit(0)  # pragma: no cover

    # Standard workflow progression
    print("=" * 70)
    _safe_print("✅ ALL TASKS COMPLETED SUCCESSFULLY")
    print("=" * 70)

    # Try to get next workflow prompt
    try:
        from ..workflows import get_next_workflow_prompt_cmd

        print("\nAuto-progressing workflow...\n")
        get_next_workflow_prompt_cmd()
    except ImportError:  # pragma: no cover
        # Workflow module not available
        print("\nAll background tasks complete.")
    except Exception as e:  # pragma: no cover
        # Workflow command failed - still report success
        print(f"\nNote: Could not auto-progress workflow: {e}")
        print("Run manually: agdt-get-next-workflow-prompt")


def tasks_clean() -> None:
    """
    Clean up expired tasks and old log files.

    Entry point: agdt-tasks-clean
    Optional state keys:
    - background.expiry_hours: Hours before tasks expire (default: 24)
    """
    from ...background_tasks import cleanup_old_logs
    from ...state import load_state

    state = load_state()

    # Parse optional expiry hours
    expiry_hours = 24  # Default 24 hours

    expiry_str = state.get("background.expiry_hours")
    if expiry_str:  # pragma: no cover
        try:
            expiry_hours = int(expiry_str)
        except ValueError:
            print(f"Warning: Invalid expiry hours '{expiry_str}', using default {expiry_hours}h")

    print(f"Cleaning up tasks older than {expiry_hours} hours...")

    # Get task count before cleanup
    tasks_before = get_background_tasks()
    count_before = len(tasks_before)

    # Clean up expired tasks
    removed_count = cleanup_expired_tasks(retention_hours=expiry_hours)

    # Clean up orphaned log files
    logs_removed = cleanup_old_logs(max_age_hours=expiry_hours)

    print("\nCleanup complete:")
    print(f"  Tasks before:    {count_before}")
    print(f"  Tasks removed:   {removed_count}")
    print(f"  Tasks remaining: {count_before - removed_count}")
    print(f"  Log files removed: {logs_removed}")


def show_other_incomplete_tasks() -> None:
    """
    Show other incomplete background tasks (not the current task_id).

    Entry point: agdt-show-other-incomplete-tasks

    This command shows any tasks in background.recentTasks that:
    - Are not in status 'completed' or 'failed'
    - Do not match the current background.task_id

    Useful for seeing if there are other tasks still running.
    """
    from ...state import get_value

    current_task_id = get_value("background.task_id") or ""

    other_incomplete = get_other_incomplete_tasks(current_task_id)

    if not other_incomplete:
        print("No other recent incomplete background tasks.")
        return

    print(f"\nOther incomplete background tasks ({len(other_incomplete)} found):")
    print(f"{'ID':<36}  {'Status':<12}  {'Command':<30}  {'Duration':<10}")
    print("-" * 95)

    for task in other_incomplete:
        status_str = f"{_status_indicator(task.status)} {task.status.value}"
        command_display = task.command[:27] + "..." if len(task.command) > 30 else task.command
        duration = _format_duration(task)

        _safe_print(f"{task.id:<36}  {status_str:<12}  {command_display:<30}  {duration:<10}")

    print()
    print('To track a specific task: agdt-task-status --id "<task-id>"')
