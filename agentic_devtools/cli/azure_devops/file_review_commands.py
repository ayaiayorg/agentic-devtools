"""
File review commands for pull request code reviews.

These commands handle file-level review actions: approve, request changes, etc.
Each command:
1. Posts a review comment (approve/request changes)
2. Marks the file as reviewed in Azure DevOps
3. Updates the review queue and triggers workflow continuation
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ...state import get_pull_request_id, get_state_dir, get_value, is_dry_run
from .auth import get_auth_headers, get_pat
from .config import AzureDevOpsConfig
from .helpers import get_repository_id, patch_comment, patch_thread_status, require_requests
from .mark_reviewed import mark_file_reviewed


def _normalize_repo_path(path: Optional[str]) -> Optional[str]:
    """Normalize a file path to repository format (/path/to/file)."""
    if not path or not path.strip():
        return None
    clean = path.strip().replace("\\", "/").strip("/")
    if not clean:  # pragma: no cover
        return None
    return f"/{clean}"


def _get_thread_file_path(thread: dict) -> Optional[str]:
    """Extract the file path from a thread's context."""
    context = thread.get("threadContext")
    if not context:
        return None

    raw_path = (
        context.get("filePath")
        or (context.get("leftFileStart") or {}).get("filePath")
        or (context.get("rightFileStart") or {}).get("filePath")
    )

    if not raw_path:  # pragma: no cover
        return None
    return raw_path.replace("\\", "/").lstrip("/")


# =============================================================================
# Queue Management
# =============================================================================


def _get_queue_path(pull_request_id: int) -> Path:
    """Get the path to the queue.json file for a pull request."""
    return get_state_dir() / "pull-request-review" / "prompts" / str(pull_request_id) / "queue.json"


def mark_file_as_submission_pending(
    pull_request_id: int,
    file_path: str,
    task_id: str,
    outcome: str,
) -> bool:
    """
    Mark a file as submission-pending in the queue.

    This is called immediately when a file review async command is invoked,
    before the background task completes. It moves the file from pending
    to a new "submission-pending" status and records the task ID.

    Args:
        pull_request_id: PR ID
        file_path: Path of file being submitted
        task_id: Background task ID tracking this submission
        outcome: Expected review outcome ('Approve', 'Changes', 'Suggest')

    Returns:
        True if file was successfully marked, False otherwise
    """
    queue_path = _get_queue_path(pull_request_id)

    if not queue_path.exists():
        print(f"Queue file not found at {queue_path}; cannot mark submission pending.")
        return False

    try:
        with open(queue_path, encoding="utf-8") as f:
            queue_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: Failed to read queue file: {e}")
        return False

    normalized_target = _normalize_repo_path(file_path)
    if not normalized_target:  # pragma: no cover
        return False

    pending = queue_data.get("pending", [])

    # Find matching entry in pending
    matched_index = None
    for idx, entry in enumerate(pending):
        entry_normalized = _normalize_repo_path(entry.get("path"))
        if entry_normalized and entry_normalized.lower() == normalized_target.lower():
            matched_index = idx
            break

    if matched_index is None:
        print(f"File '{file_path}' not found in pending queue.")
        return False

    # Update the entry to submission-pending
    pending[matched_index]["status"] = "submission-pending"
    pending[matched_index]["taskId"] = task_id
    pending[matched_index]["outcome"] = outcome
    pending[matched_index]["submittedUtc"] = datetime.now(timezone.utc).isoformat()
    # Clean up any failure fields from previous attempts
    pending[matched_index].pop("failedUtc", None)
    pending[matched_index].pop("errorMessage", None)

    queue_data["lastUpdatedUtc"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, indent=2)
        return True
    except OSError as e:  # pragma: no cover
        print(f"Warning: Failed to write queue file: {e}")
        return False


def update_submission_to_completed(
    pull_request_id: int,
    file_path: str,
) -> bool:
    """
    Update a submission-pending file to completed status.

    Called by the background task after successfully posting the review.

    Args:
        pull_request_id: PR ID
        file_path: Path of reviewed file

    Returns:
        True if updated successfully, False otherwise
    """
    queue_path = _get_queue_path(pull_request_id)

    if not queue_path.exists():
        return False

    try:
        with open(queue_path, encoding="utf-8") as f:
            queue_data = json.load(f)
    except (json.JSONDecodeError, OSError):  # pragma: no cover
        return False

    normalized_target = _normalize_repo_path(file_path)
    if not normalized_target:  # pragma: no cover
        return False

    pending = queue_data.get("pending", [])
    completed = queue_data.get("completed", [])

    # Find matching entry (should be submission-pending)
    matched_entry = None
    remaining_pending = []

    for entry in pending:
        entry_normalized = _normalize_repo_path(entry.get("path"))
        if entry_normalized and entry_normalized.lower() == normalized_target.lower():
            matched_entry = entry
        else:
            remaining_pending.append(entry)

    if not matched_entry:
        return False

    # Update to completed
    matched_entry["status"] = "completed"
    matched_entry["completedUtc"] = datetime.now(timezone.utc).isoformat()
    # Remove task tracking fields
    matched_entry.pop("taskId", None)
    matched_entry.pop("submittedUtc", None)

    completed.append(matched_entry)

    queue_data["pending"] = remaining_pending
    queue_data["completed"] = completed
    queue_data["lastUpdatedUtc"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, indent=2)
        return True
    except OSError:  # pragma: no cover
        return False


def update_submission_to_failed(
    pull_request_id: int,
    file_path: str,
    error_message: str,
) -> bool:
    """
    Update a submission-pending file to failed status.

    Called by the background task if the review submission fails.

    Args:
        pull_request_id: PR ID
        file_path: Path of file that failed
        error_message: Error description

    Returns:
        True if updated successfully, False otherwise
    """
    queue_path = _get_queue_path(pull_request_id)

    if not queue_path.exists():
        return False

    try:
        with open(queue_path, encoding="utf-8") as f:
            queue_data = json.load(f)
    except (json.JSONDecodeError, OSError):  # pragma: no cover
        return False

    normalized_target = _normalize_repo_path(file_path)
    if not normalized_target:  # pragma: no cover
        return False

    pending = queue_data.get("pending", [])

    # Find and update matching entry
    for entry in pending:
        entry_normalized = _normalize_repo_path(entry.get("path"))
        if entry_normalized and entry_normalized.lower() == normalized_target.lower():
            entry["status"] = "failed"
            entry["failedUtc"] = datetime.now(timezone.utc).isoformat()
            entry["errorMessage"] = error_message
            break

    queue_data["lastUpdatedUtc"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, indent=2)
        return True
    except OSError:  # pragma: no cover
        return False


def get_failed_submissions(pull_request_id: int) -> list[dict]:
    """
    Get all failed submission entries from the queue.

    Args:
        pull_request_id: PR ID

    Returns:
        List of failed queue entries with file path and error info
    """
    queue_path = _get_queue_path(pull_request_id)

    if not queue_path.exists():
        return []

    try:
        with open(queue_path, encoding="utf-8") as f:
            queue_data = json.load(f)
    except (json.JSONDecodeError, OSError):  # pragma: no cover
        return []

    pending = queue_data.get("pending", [])
    return [entry for entry in pending if entry.get("status") == "failed"]


def reset_failed_submission(pull_request_id: int, file_path: str) -> bool:
    """
    Reset a failed submission back to pending status for retry.

    Args:
        pull_request_id: PR ID
        file_path: Path of failed file to reset

    Returns:
        True if reset successfully, False otherwise
    """
    queue_path = _get_queue_path(pull_request_id)

    if not queue_path.exists():  # pragma: no cover
        return False

    try:
        with open(queue_path, encoding="utf-8") as f:
            queue_data = json.load(f)
    except (json.JSONDecodeError, OSError):  # pragma: no cover
        return False

    normalized_target = _normalize_repo_path(file_path)
    if not normalized_target:  # pragma: no cover
        return False

    pending = queue_data.get("pending", [])

    # Find and reset matching failed entry
    for entry in pending:
        entry_normalized = _normalize_repo_path(entry.get("path"))
        if entry_normalized and entry_normalized.lower() == normalized_target.lower():
            if entry.get("status") == "failed":
                entry["status"] = "pending"
                # Remove failure tracking fields
                entry.pop("taskId", None)
                entry.pop("submittedUtc", None)
                entry.pop("failedUtc", None)
                entry.pop("errorMessage", None)
                entry.pop("outcome", None)
                break

    queue_data["lastUpdatedUtc"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, indent=2)
        return True
    except OSError:  # pragma: no cover
        return False


def sync_submission_pending_with_tasks(pull_request_id: int) -> None:
    """
    Sync submission-pending entries with their background task status.

    This checks all submission-pending entries and:
    - If task completed successfully: moves entry to completed
    - If task failed: marks entry as failed with error message
    - If task still running: leaves entry unchanged

    Called at the start of print_next_file_prompt() to ensure queue state
    is accurate before showing the next file.

    Args:
        pull_request_id: PR ID
    """
    from ...task_state import TaskStatus, get_task_by_id

    queue_path = _get_queue_path(pull_request_id)

    if not queue_path.exists():
        return

    try:
        with open(queue_path, encoding="utf-8") as f:
            queue_data = json.load(f)
    except (json.JSONDecodeError, OSError):  # pragma: no cover
        return

    pending = queue_data.get("pending", [])
    completed = queue_data.get("completed", [])
    modified = False

    # Process submission-pending entries
    entries_to_complete = []
    for entry in pending:
        if entry.get("status") != "submission-pending":
            continue

        task_id = entry.get("taskId")
        if not task_id:  # pragma: no cover
            continue

        task = get_task_by_id(task_id)
        if not task:
            # Task not found - mark as failed
            entry["status"] = "failed"
            entry["failedUtc"] = datetime.now(timezone.utc).isoformat()
            entry["errorMessage"] = "Background task not found"
            modified = True
        elif task.status == TaskStatus.COMPLETED:
            # Task completed successfully - move to completed
            entries_to_complete.append(entry)
            modified = True
        elif task.status == TaskStatus.FAILED:
            # Task failed - mark entry as failed
            entry["status"] = "failed"
            entry["failedUtc"] = datetime.now(timezone.utc).isoformat()
            error_msg = task.error_message or f"Task failed with exit code {task.exit_code}"
            entry["errorMessage"] = error_msg
            modified = True
        # If task is pending or running, leave entry unchanged

    # Move completed entries to completed list
    for entry in entries_to_complete:
        pending.remove(entry)
        entry["status"] = "completed"
        entry["completedUtc"] = datetime.now(timezone.utc).isoformat()
        # Clean up task tracking fields
        entry.pop("taskId", None)
        entry.pop("submittedUtc", None)
        entry.pop("failedUtc", None)
        entry.pop("errorMessage", None)
        completed.append(entry)

    if modified:
        queue_data["lastUpdatedUtc"] = datetime.now(timezone.utc).isoformat()
        try:
            with open(queue_path, "w", encoding="utf-8") as f:
                json.dump(queue_data, f, indent=2)
        except OSError:  # pragma: no cover
            pass


def trigger_in_progress_for_file(
    pull_request_id: int,
    file_path: str,
    dry_run: bool = False,
) -> None:
    """
    Trigger "In Progress" status for a file when its review prompt is served.

    If the file's status in review-state.json is "unreviewed", this function:
    1. Updates the file status to "in-progress"
    2. PATCHes the file summary comment with the "In Progress" template
    3. Recalculates folder status and PATCHes if changed
    4. Recalculates overall PR status and PATCHes if changed
    5. Saves updated review-state.json

    If the file status is already "in-progress", "approved", or "needs-work" → no-op.

    Args:
        pull_request_id: PR ID
        file_path: File path to trigger status for
        dry_run: If True, skip API calls and print dry-run messages
    """
    from .review_scaffold import _build_pr_base_url
    from .review_state import (
        ReviewStatus,
        load_review_state,
        normalize_file_path,
        save_review_state,
        update_file_status,
    )
    from .review_templates import render_file_summary
    from .status_cascade import cascade_status_update, execute_cascade

    try:
        review_state = load_review_state(pull_request_id)
    except FileNotFoundError:
        return  # No review state yet; skip

    normalized = normalize_file_path(file_path)
    file_entry = review_state.files.get(normalized)
    if file_entry is None:
        return  # File not in review state; skip

    if file_entry.status != ReviewStatus.UNREVIEWED.value:
        return  # No-op for non-unreviewed files

    # Update file status to "in-progress"
    update_file_status(review_state, file_path, ReviewStatus.IN_PROGRESS.value)
    # Refresh local reference after in-place mutation
    file_entry = review_state.files[normalized]

    config = AzureDevOpsConfig.from_state()
    base_url = _build_pr_base_url(config, pull_request_id)

    # Use repoId already stored in review state (set during scaffolding)
    # to avoid shelling out to `az repos show` on every prompt.
    repo_id = review_state.repoId

    if dry_run:
        requests_module = None
        auth_headers: dict = {}
    else:
        requests_module = require_requests()
        auth_headers = get_auth_headers(get_pat())

    # PATCH file summary comment content; file thread status stays "active" per spec
    file_content = render_file_summary(file_entry, file_entry.suggestions, base_url)
    patch_comment(
        requests_module=requests_module,
        headers=auth_headers,
        config=config,
        repo_id=repo_id,
        pull_request_id=pull_request_id,
        thread_id=file_entry.threadId,
        comment_id=file_entry.commentId,
        new_content=file_content,
        dry_run=dry_run,
    )

    # Cascade folder and overall summary updates. Persist the updated
    # review_state even if downstream cascade execution fails, so the
    # local state reflects the already-PATCHed file comment.
    try:
        ops = cascade_status_update(review_state, file_path, base_url)
        execute_cascade(ops, requests_module, auth_headers, config, repo_id, pull_request_id, dry_run=dry_run)
    finally:
        if not dry_run:
            save_review_state(review_state)


def print_next_file_prompt(pull_request_id: int) -> None:
    """
    Print the prompt for the next file to review, checking for failures first.

    This is the main function called after async submission to continue the workflow.
    It first syncs submission-pending entries with their background task status,
    then checks for failed submissions, and finally shows the next pending file.

    Args:
        pull_request_id: PR ID
    """
    # Sync submission-pending entries with background task status
    sync_submission_pending_with_tasks(pull_request_id)

    # Check for failed submissions first
    failed = get_failed_submissions(pull_request_id)
    if failed:
        print("")
        print("=" * 60)
        print(f"⚠️  FAILED SUBMISSIONS ({len(failed)})")
        print("=" * 60)
        print("")
        for entry in failed:
            print(f"  File: {entry.get('path')}")
            print(f"  Outcome: {entry.get('outcome', 'Unknown')}")
            print(f"  Error: {entry.get('errorMessage', 'Unknown error')}")
            print("")
        print("Action required:")
        print("  1. Review the error message above")
        print("  2. If submission parameters were wrong, adjust and resubmit")
        print("     (e.g., fix line numbers, content formatting)")
        print("  3. If error appears transient/external, simply resubmit as-is")
        print("")
        print("Resubmit using: agdt-approve-file, dfly-request-changes, or")
        print("                agdt-request-changes-with-suggestion")
        print("")
        return

    # Get queue status
    status = get_queue_status(pull_request_id)

    # Trigger "In Progress" when serving the next file's prompt
    if not status["all_complete"] and status["current_file"]:
        try:
            trigger_in_progress_for_file(
                pull_request_id=pull_request_id,
                file_path=status["current_file"],
                dry_run=is_dry_run(),
            )
        except Exception as e:
            print(f"Warning: Could not trigger in-progress status: {e}", file=sys.stderr)

    print("")
    print("=" * 60)

    if status["all_complete"]:
        # All files reviewed - summary will be triggered automatically
        # when the task wait detects completion via _try_advance_pr_review_to_summary
        print("ALL FILES REVIEWED - PENDING SUBMISSION COMPLETION")
        print("=" * 60)
        print("")
        print(f"Total files reviewed: {status['completed_count']}")
        print("")
        print("Some file review submissions are still being processed in the background.")
        print("")
        print("IMPORTANT: The PR summary will be generated AUTOMATICALLY once all")
        print("submissions complete. Do NOT manually trigger dfly-generate-pr-summary.")
        print("")
        print("YOUR ONLY ACTION: Run agdt-task-wait")
        print("")
        print("This will wait for submissions to complete, auto-trigger the summary,")
        print("and provide next steps when everything is done.")
    else:
        # Count submission-pending files
        queue_path = _get_queue_path(pull_request_id)
        submission_pending_count = 0
        if queue_path.exists():
            try:
                with open(queue_path, encoding="utf-8") as f:
                    queue_data = json.load(f)
                submission_pending_count = sum(
                    1 for entry in queue_data.get("pending", []) if entry.get("status") == "submission-pending"
                )
            except (json.JSONDecodeError, OSError):  # pragma: no cover
                pass

        pending_count = status["pending_count"] - submission_pending_count
        print(f"QUEUE STATUS: {status['completed_count']} completed, {pending_count} pending", end="")
        if submission_pending_count > 0:  # pragma: no cover
            print(f", {submission_pending_count} submitting")
        else:
            print()
        print("=" * 60)
        print("")

        if status["current_file"] and status["prompt_file_path"]:  # pragma: no cover
            print(f"Next file: {status['current_file']}")
            print(f"Prompt: {status['prompt_file_path']}")
        else:
            print("Continue with the next file in the queue.")
            print(f"Queue location: scripts/temp/pull-request-review/prompts/{pull_request_id}/queue.json")

    print("")


def _update_queue_after_review(
    pull_request_id: int,
    file_path: str,
    outcome: str,
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    Update the review queue after completing a file review.

    Moves the file from pending (or submission-pending) to completed,
    updating status and timestamp. Also cleans up any task tracking fields.

    Args:
        pull_request_id: PR ID
        file_path: Path of reviewed file
        outcome: Review outcome ('Approve', 'Changes', 'Suggest')
        dry_run: If True, only print what would be done

    Returns:
        Tuple of (pending_count, completed_count) after update
    """
    queue_path = _get_queue_path(pull_request_id)

    if not queue_path.exists():
        print(f"Queue file not found at {queue_path}; skipping queue update.")
        return 0, 0

    try:
        with open(queue_path, encoding="utf-8") as f:
            queue_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:  # pragma: no cover
        print(f"Warning: Failed to read queue file: {e}")
        return 0, 0

    normalized_target = _normalize_repo_path(file_path)
    if not normalized_target:  # pragma: no cover
        return len(queue_data.get("pending", [])), len(queue_data.get("completed", []))

    pending = queue_data.get("pending", [])
    completed = queue_data.get("completed", [])

    # Find matching entry in pending (handles both "pending" and "submission-pending" status)
    matched_entry = None
    remaining_pending = []

    for entry in pending:
        entry_normalized = _normalize_repo_path(entry.get("path"))
        if entry_normalized and entry_normalized.lower() == normalized_target.lower():
            matched_entry = entry
        else:
            remaining_pending.append(entry)

    if not matched_entry:  # pragma: no cover
        print(f"File '{file_path}' not found in pending queue.")
        return len(pending), len(completed)

    if dry_run:
        print(f"DRY-RUN: Would move '{file_path}' from pending to completed.")
        return len(pending) - 1, len(completed) + 1

    # Update the entry - clean up any submission tracking fields
    matched_entry["status"] = "completed"
    matched_entry["outcome"] = outcome
    matched_entry["completedUtc"] = datetime.now(timezone.utc).isoformat()

    # Remove submission tracking fields if present
    matched_entry.pop("taskId", None)
    matched_entry.pop("submittedUtc", None)
    matched_entry.pop("failedUtc", None)
    matched_entry.pop("errorMessage", None)

    completed.append(matched_entry)

    # Update queue data
    queue_data["pending"] = remaining_pending
    queue_data["completed"] = completed
    queue_data["lastUpdatedUtc"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, indent=2)
    except OSError as e:  # pragma: no cover
        print(f"Warning: Failed to write queue file: {e}")

    return len(remaining_pending), len(completed)


def _trigger_workflow_continuation(
    pull_request_id: int,
    pending_count: int,
    completed_count: int,
) -> None:
    """
    Print status after a file review and guide user to next step.

    If there are more files pending, prints instructions to continue.
    If all files are reviewed, prints completion message.

    Note: Summary generation is NOT triggered here. It is handled by the
    task completion handler in tasks/commands.py when all async file
    submissions have completed. This prevents duplicate summary comments.

    Args:
        pull_request_id: PR ID
        pending_count: Number of files still pending
        completed_count: Number of files completed
    """
    print("")
    print("=" * 60)

    if pending_count > 0:
        print(f"QUEUE STATUS: {completed_count} completed, {pending_count} remaining")
        print("=" * 60)
        print("")
        print("Continue with the next file in the queue.")
        print(f"Queue location: scripts/temp/pull-request-review/prompts/{pull_request_id}/queue.json")
    else:
        print("ALL FILES REVIEWED")
        print("=" * 60)
        print("")
        print(f"Total files reviewed: {completed_count}")
        print("")
        print("Summary generation will be triggered automatically when all")
        print("background file submission tasks complete.")
        print("")
        print("Use 'agdt-task-wait' to monitor pending submissions.")

    print("")


def get_queue_status(pull_request_id: int) -> dict:
    """
    Get the current status of the file review queue.

    This function reads the queue.json file and returns status information
    suitable for populating workflow prompt templates.

    Args:
        pull_request_id: PR ID to get queue status for

    Returns:
        Dictionary with queue status:
        - pull_request_id: The PR ID
        - completed_count: Number of files reviewed
        - pending_count: Number of files still pending (excludes submission-pending/failed)
        - submission_pending_count: Number of files being submitted
        - failed_count: Number of failed submissions
        - total_count: Total number of files
        - current_file: Path of next file to review (or None if done)
        - prompt_file_path: Full path to the current file's prompt (or None)
        - all_complete: True if all files have been reviewed
    """
    queue_path = _get_queue_path(pull_request_id)

    result = {
        "pull_request_id": pull_request_id,
        "completed_count": 0,
        "pending_count": 0,
        "submission_pending_count": 0,
        "failed_count": 0,
        "total_count": 0,
        "current_file": None,
        "prompt_file_path": None,
        "all_complete": False,
    }

    if not queue_path.exists():
        return result

    try:
        with open(queue_path, encoding="utf-8") as f:
            queue_data = json.load(f)
    except (json.JSONDecodeError, OSError):  # pragma: no cover
        return result

    pending = queue_data.get("pending", [])
    completed = queue_data.get("completed", [])

    # Categorize pending items by status
    truly_pending = []
    submission_pending = []
    failed = []

    for entry in pending:
        status = entry.get("status", "pending")
        if status == "submission-pending":
            submission_pending.append(entry)
        elif status == "failed":
            failed.append(entry)
        else:
            truly_pending.append(entry)

    result["pending_count"] = len(truly_pending)
    result["submission_pending_count"] = len(submission_pending)
    result["failed_count"] = len(failed)
    result["completed_count"] = len(completed)
    result["total_count"] = len(pending) + len(completed)

    # All complete when no truly pending files remain
    # (submission-pending and failed are handled separately)
    result["all_complete"] = len(truly_pending) == 0 and len(failed) == 0

    # Get the next file to review (skip submission-pending and failed)
    if truly_pending:
        next_file = truly_pending[0]
        file_path = next_file.get("path", "")
        result["current_file"] = file_path

        # Use the prompt path from the queue item (already computed during prompt generation)
        prompt_path = next_file.get("promptPath", "")
        if prompt_path and Path(prompt_path).exists():  # pragma: no cover
            result["prompt_file_path"] = prompt_path

    return result


def _resolve_file_threads(
    requests,
    headers: dict,
    config: AzureDevOpsConfig,
    repo_id: str,
    pull_request_id: int,
    target_path: str,
    dry_run: bool = False,
) -> int:
    """
    Resolve (close) all active threads for a specific file.

    Returns:
        Number of threads resolved.
    """
    normalized_target = _normalize_repo_path(target_path)
    if not normalized_target:
        return 0

    project_encoded = config.project.replace(" ", "%20")
    threads_url = (
        f"{config.organization}/{project_encoded}/_apis/git/repositories/{repo_id}"
        f"/pullRequests/{pull_request_id}/threads?api-version=7.1-preview.1"
    )

    try:
        response = requests.get(threads_url, headers=headers, timeout=30)
        response.raise_for_status()
        threads_data = response.json()
    except Exception as e:
        print(f"Warning: Failed to retrieve threads: {e}", file=sys.stderr)
        return 0

    thread_items = threads_data.get("value", [])
    matching = []

    for thread in thread_items:
        status = thread.get("status")
        if status not in ("active", "pending"):
            continue

        thread_path = _get_thread_file_path(thread)
        if not thread_path:  # pragma: no cover
            continue

        normalized_thread = _normalize_repo_path(thread_path)
        if normalized_thread and normalized_thread.lower() == normalized_target.lower():
            matching.append(thread)

    if not matching:
        print(f"No unresolved comment threads to resolve for '{target_path}'.")
        return 0

    print(f"Resolving {len(matching)} thread(s) for '{target_path}'...")

    resolved_count = 0
    for thread in matching:
        thread_id = thread.get("id")
        if not thread_id:  # pragma: no cover
            continue

        if dry_run:
            print(f"DRY-RUN: Would resolve thread {thread_id} for {target_path}")
            resolved_count += 1
            continue

        resolve_url = (
            f"{config.organization}/{project_encoded}/_apis/git/repositories/{repo_id}"
            f"/pullRequests/{pull_request_id}/threads/{thread_id}?api-version=7.1-preview.1"
        )
        try:
            resp = requests.patch(resolve_url, headers=headers, json={"status": "closed"}, timeout=30)
            resp.raise_for_status()
            resolved_count += 1
        except Exception as e:
            print(f"Failed to resolve thread {thread_id}: {e}", file=sys.stderr)

    if not dry_run and resolved_count > 0:
        print(f"Comment threads for '{target_path}' resolved.")

    return resolved_count


def approve_file() -> None:  # pragma: no cover
    """
    Approve a file in a pull request review.

    When review-state.json exists (new PATCH flow):
    1. Loads review state and updates file status to Approved
    2. PATCHes the existing file summary comment with rendered markdown
    3. PATCHes the file thread status to "closed"
    4. Marks the file as reviewed in Azure DevOps
    5. Cascades folder and PR summary updates via PATCH
    6. Saves updated review state
    7. Updates the review queue and triggers workflow continuation

    When review-state.json does not exist (legacy fallback):
    1. Resolves any existing threads for the file
    2. Posts a new approval comment
    3. Marks the file as reviewed and updates the queue

    State keys read:
        - pull_request_id (required): Pull request ID
        - file_review.file_path (required): Path of file to approve
        - file_review.summary (required): Approval summary text
        - content (deprecated): Falls back to file_review.summary with a warning
        - dry_run: If true, only print what would be done

    Raises:
        SystemExit: On validation or execution errors.
    """
    requests = require_requests()
    config = AzureDevOpsConfig.from_state()
    dry_run = is_dry_run()
    pull_request_id = get_pull_request_id(required=True)

    file_path = get_value("file_review.file_path")
    if not file_path:
        print("Error: 'file_review.file_path' is required.", file=sys.stderr)
        print("Set it with: agdt-set file_review.file_path <path>", file=sys.stderr)
        sys.exit(1)

    # Support file_review.summary (new) with content as deprecated fallback
    summary = get_value("file_review.summary")
    if not summary:
        content = get_value("content")
        if content:
            print(
                "Warning: 'content' is deprecated for agdt-approve-file. Use 'file_review.summary' instead.",
                file=sys.stderr,
            )
            summary = content
    if not summary:
        print(
            "Error: 'file_review.summary' (or 'content', deprecated) is required for approval.",
            file=sys.stderr,
        )
        print("Set it with: agdt-set file_review.summary '<approval summary>'", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        print(f"DRY-RUN: Would approve file '{file_path}' on PR {pull_request_id}")
        print(f"  Organization: {config.organization}")
        print(f"  Project: {config.project}")
        print(f"  Repository: {config.repository}")
        print(f"Summary:\n{summary}")
        return

    pat = get_pat()
    headers = get_auth_headers(pat)

    print(f"Resolving repository ID for '{config.repository}'...")
    repo_id = get_repository_id(config.organization, config.project, config.repository)

    # Try new PATCH flow (requires review-state.json)
    try:
        from .review_scaffold import _build_pr_base_url
        from .review_state import (
            ReviewStatus,
            load_review_state,
            normalize_file_path,
            save_review_state,
            update_file_status,
        )
        from .review_templates import render_file_summary
        from .status_cascade import cascade_status_update, execute_cascade

        review_state = load_review_state(pull_request_id)
        base_url = _build_pr_base_url(config, pull_request_id)

        # Update file status to Approved with summary text
        update_file_status(review_state, file_path, ReviewStatus.APPROVED.value, summary=summary)

        normalized = normalize_file_path(file_path)
        file_entry = review_state.files[normalized]

        # PATCH file summary comment with regenerated markdown
        file_content = render_file_summary(file_entry, [], base_url)
        patch_comment(
            requests_module=requests,
            headers=headers,
            config=config,
            repo_id=repo_id,
            pull_request_id=pull_request_id,
            thread_id=file_entry.threadId,
            comment_id=file_entry.commentId,
            new_content=file_content,
            dry_run=dry_run,
        )

        # PATCH file thread status to closed
        patch_thread_status(
            requests_module=requests,
            headers=headers,
            config=config,
            repo_id=repo_id,
            pull_request_id=pull_request_id,
            thread_id=file_entry.threadId,
            status="closed",
            dry_run=dry_run,
        )

        # Mark file as reviewed in Azure DevOps
        mark_file_reviewed(
            file_path=file_path,
            pull_request_id=pull_request_id,
            config=config,
            repo_id=repo_id,
            dry_run=dry_run,
        )

        # Cascade: update folder and overall PR summary via PATCH
        patch_operations = cascade_status_update(review_state, file_path, base_url)
        execute_cascade(
            patch_operations=patch_operations,
            requests_module=requests,
            headers=headers,
            config=config,
            repo_id=repo_id,
            pull_request_id=pull_request_id,
            dry_run=dry_run,
        )

        # Save updated review state
        save_review_state(review_state)

    except FileNotFoundError:
        # Legacy fallback: create new thread (no review-state.json available)
        print("Note: No review-state.json found. Using legacy approval flow.")
        from ...state import set_value
        from .commands import add_pull_request_comment  # Avoid circular import

        # Step 1: Resolve any existing threads for this file
        _resolve_file_threads(requests, headers, config, repo_id, pull_request_id, file_path, dry_run)

        # Step 2: Post approval comment
        set_value("path", file_path)
        set_value("content", summary)
        set_value("is_pull_request_approval", "true")
        set_value("leave_thread_active", "false")

        add_pull_request_comment()

        # Step 3: Mark file as reviewed in Azure DevOps
        mark_file_reviewed(
            file_path=file_path,
            pull_request_id=pull_request_id,
            config=config,
            repo_id=repo_id,
            dry_run=dry_run,
        )

    # Update the review queue
    pending_count, completed_count = _update_queue_after_review(
        pull_request_id=pull_request_id,
        file_path=file_path,
        outcome="Approve",
        dry_run=dry_run,
    )

    print(f"File '{file_path}' approved successfully.")

    # Trigger workflow continuation
    _trigger_workflow_continuation(pull_request_id, pending_count, completed_count)


def submit_file_review() -> None:  # pragma: no cover
    """
    Submit a file review (approve, request changes, or suggest).

    This function:
    1. Posts a review comment
    2. Marks the file as reviewed in Azure DevOps
    3. Updates the review queue
    4. Triggers workflow continuation

    State keys read:
        - pull_request_id (required): Pull request ID
        - file_review.file_path (required): Path of file being reviewed
        - file_review.outcome (required): 'Approve', 'Changes', or 'Suggest'
        - content (required): Review comment content
        - line (optional): Line number for comment (required for Changes/Suggest)
        - end_line (optional): End line for multi-line comment
        - dry_run: If true, only print what would be done

    Raises:
        SystemExit: On validation or execution errors.
    """
    config = AzureDevOpsConfig.from_state()
    dry_run = is_dry_run()
    pull_request_id = get_pull_request_id(required=True)

    file_path = get_value("file_review.file_path")
    if not file_path:
        print("Error: 'file_review.file_path' is required.", file=sys.stderr)
        sys.exit(1)

    outcome = get_value("file_review.outcome")
    if not outcome or outcome not in ("Approve", "Changes", "Suggest"):
        print(
            "Error: 'file_review.outcome' must be 'Approve', 'Changes', or 'Suggest'.",
            file=sys.stderr,
        )
        sys.exit(1)

    content = get_value("content")
    if not content:
        print("Error: 'content' is required for review comment.", file=sys.stderr)
        sys.exit(1)

    line = get_value("line")
    end_line = get_value("end_line")

    # For change requests, line is required
    if outcome != "Approve" and line is None:
        print("Error: 'line' is required for change requests.", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        print(f"DRY-RUN: Would submit {outcome} review for '{file_path}' on PR {pull_request_id}")
        print("--- Comment Preview ---")
        print(content)
        print("-----------------------")
        if line is not None:
            range_text = f"{line}-{end_line}" if end_line and end_line != line else str(line)
            print(f"Line context: {range_text}")
        else:
            print("No line metadata (file-level approval).")
        return

    # Import here to avoid circular import
    from ...state import set_value
    from .commands import add_pull_request_comment

    # Step 1: Post review comment
    set_value("path", file_path)
    set_value("is_pull_request_approval", "true" if outcome == "Approve" else "false")
    set_value("leave_thread_active", "false" if outcome == "Approve" else "true")

    add_pull_request_comment()

    # Step 2: Mark file as reviewed in Azure DevOps
    pat = get_pat()
    get_auth_headers(pat)  # Ensure auth is set up
    repo_id = get_repository_id(config.organization, config.project, config.repository)

    mark_file_reviewed(
        file_path=file_path,
        pull_request_id=pull_request_id,
        config=config,
        repo_id=repo_id,
        dry_run=dry_run,
    )

    # Step 3: Update the review queue
    pending_count, completed_count = _update_queue_after_review(
        pull_request_id=pull_request_id,
        file_path=file_path,
        outcome=outcome,
        dry_run=dry_run,
    )

    print(f"File review ({outcome}) submitted for '{file_path}'.")

    # Step 4: Trigger workflow continuation
    _trigger_workflow_continuation(pull_request_id, pending_count, completed_count)


def request_changes() -> None:
    """
    Request changes on a file in a pull request review.

    Wrapper around submit_file_review with outcome='Changes'.

    State keys read:
        - pull_request_id (required): Pull request ID
        - file_review.file_path (required): Path of file
        - content (required): Change request comment
        - line (required): Line number for comment
        - end_line (optional): End line for multi-line comment
        - dry_run: If true, only print what would be done
    """
    from ...state import set_value

    set_value("file_review.outcome", "Changes")
    submit_file_review()


def request_changes_with_suggestion() -> None:
    """
    Request changes with a suggestion on a file in a pull request review.

    Wrapper around submit_file_review with outcome='Suggest'.

    State keys read:
        - pull_request_id (required): Pull request ID
        - file_review.file_path (required): Path of file
        - content (required): Suggestion comment (should include code suggestion)
        - line (required): Line number for comment
        - end_line (optional): End line for multi-line comment
        - dry_run: If true, only print what would be done
    """
    from ...state import set_value

    set_value("file_review.outcome", "Suggest")
    submit_file_review()
