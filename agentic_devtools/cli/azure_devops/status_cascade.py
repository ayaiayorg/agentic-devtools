"""Status derivation and cascade update logic for PR review state.

Provides functions to:
- Derive folder and overall PR status from file/folder statuses
- Compute PATCH operations needed after a file status change
- Execute those PATCH operations against the Azure DevOps API
"""

from dataclasses import dataclass
from typing import Dict, List

from .config import AzureDevOpsConfig
from .helpers import patch_comment, patch_thread_status
from .review_state import ReviewState, ReviewStatus, normalize_file_path
from .review_templates import render_folder_summary, render_overall_summary

# Thread status mapping: review status → Azure DevOps thread status
_THREAD_STATUS_MAP: Dict[str, str] = {
    ReviewStatus.UNREVIEWED.value: "active",
    ReviewStatus.IN_PROGRESS.value: "active",
    ReviewStatus.APPROVED.value: "closed",
    ReviewStatus.NEEDS_WORK.value: "active",
}

# Statuses that indicate a file/folder review is complete
_COMPLETE_STATUSES = frozenset({ReviewStatus.APPROVED.value, ReviewStatus.NEEDS_WORK.value})


@dataclass
class PatchOperation:
    """A pair of PATCH operations for a review comment: content + thread status."""

    thread_id: int
    comment_id: int
    new_content: str
    thread_status: str


def derive_folder_status(state: ReviewState, folder_name: str) -> str:
    """Compute the derived status for a folder based on its file statuses.

    Status Derivation Rules:
    - No files or all files unreviewed → unreviewed
    - At least 1 file started, not all complete → in-progress
    - All files complete, all Approved → approved
    - All files complete, any Needs Work → needs-work

    Args:
        state: Full ReviewState containing files.
        folder_name: Name of the folder to derive status for.

    Returns:
        Derived status string (a ReviewStatus value).

    Raises:
        KeyError: If folder_name is not found in review state.
    """
    if folder_name not in state.folders:
        raise KeyError(f"Folder not found in review state: {folder_name}")

    folder = state.folders[folder_name]
    file_statuses = [state.files[fp].status for fp in folder.files if fp in state.files]

    if not file_statuses:
        return ReviewStatus.UNREVIEWED.value

    any_started = any(s != ReviewStatus.UNREVIEWED.value for s in file_statuses)
    all_complete = all(s in _COMPLETE_STATUSES for s in file_statuses)

    if not any_started:
        return ReviewStatus.UNREVIEWED.value
    elif not all_complete:
        return ReviewStatus.IN_PROGRESS.value
    elif any(s == ReviewStatus.NEEDS_WORK.value for s in file_statuses):
        return ReviewStatus.NEEDS_WORK.value
    else:
        return ReviewStatus.APPROVED.value


def derive_overall_status(state: ReviewState) -> str:
    """Compute the derived overall PR status based on folder statuses.

    Status Derivation Rules:
    - No folders or all folders unreviewed → unreviewed
    - At least 1 folder started, not all complete → in-progress
    - All folders complete, all Approved → approved
    - All folders complete, any Needs Work → needs-work

    Args:
        state: Full ReviewState containing folders.

    Returns:
        Derived status string (a ReviewStatus value).
    """
    folder_statuses = [f.status for f in state.folders.values()]

    if not folder_statuses:
        return ReviewStatus.UNREVIEWED.value

    any_started = any(s != ReviewStatus.UNREVIEWED.value for s in folder_statuses)
    all_complete = all(s in _COMPLETE_STATUSES for s in folder_statuses)

    if not any_started:
        return ReviewStatus.UNREVIEWED.value
    elif not all_complete:
        return ReviewStatus.IN_PROGRESS.value
    elif any(s == ReviewStatus.NEEDS_WORK.value for s in folder_statuses):
        return ReviewStatus.NEEDS_WORK.value
    else:
        return ReviewStatus.APPROVED.value


def cascade_status_update(
    state: ReviewState,
    file_path: str,
    base_url: str,
) -> List[PatchOperation]:
    """Compute all PATCH operations needed after a file's status has changed.

    Updates the folder and overall summary statuses in the state object,
    then returns the PATCH operations needed to sync Azure DevOps comments
    and thread statuses.

    Args:
        state: Full ReviewState (mutated in-place with new folder/overall statuses).
        file_path: Path of the file whose status has changed.
        base_url: PR root URL for generating markdown content.

    Returns:
        List of PatchOperation objects to execute via execute_cascade.

    Raises:
        KeyError: If file_path is not found in review state.
        KeyError: If the file's folder is not found in review state.
    """
    normalized = normalize_file_path(file_path)
    if normalized not in state.files:
        raise KeyError(f"File not found in review state: {normalized}")

    file_entry = state.files[normalized]
    folder_name = file_entry.folder

    if folder_name not in state.folders:
        raise KeyError(f"Folder not found in review state: {folder_name}")

    # Derive and update folder status
    new_folder_status = derive_folder_status(state, folder_name)
    folder_entry = state.folders[folder_name]
    folder_entry.status = new_folder_status

    # Derive and update overall summary status
    new_overall_status = derive_overall_status(state)
    state.overallSummary.status = new_overall_status

    # Build PATCH operations
    ops: List[PatchOperation] = []

    # Folder comment PATCH
    folder_content = render_folder_summary(folder_name, folder_entry, state.files, base_url)
    ops.append(
        PatchOperation(
            thread_id=folder_entry.threadId,
            comment_id=folder_entry.commentId,
            new_content=folder_content,
            thread_status=_THREAD_STATUS_MAP[new_folder_status],
        )
    )

    # Overall summary comment PATCH
    overall_content = render_overall_summary(state, base_url)
    ops.append(
        PatchOperation(
            thread_id=state.overallSummary.threadId,
            comment_id=state.overallSummary.commentId,
            new_content=overall_content,
            thread_status=_THREAD_STATUS_MAP[new_overall_status],
        )
    )

    return ops


def execute_cascade(
    patch_operations: List[PatchOperation],
    requests_module,
    headers: Dict[str, str],
    config: AzureDevOpsConfig,
    repo_id: str,
    pull_request_id: int,
    dry_run: bool = False,
) -> None:
    """Execute all PATCH operations against the Azure DevOps API.

    For each PatchOperation, updates both the comment content and the
    thread status via separate PATCH calls.

    Args:
        patch_operations: List of PatchOperation objects to execute.
        requests_module: The requests module.
        headers: Auth headers for API calls.
        config: Azure DevOps configuration.
        repo_id: Repository ID.
        pull_request_id: Pull request ID.
        dry_run: If True, skip API calls and print dry-run messages.
    """
    for op in patch_operations:
        patch_comment(
            requests_module=requests_module,
            headers=headers,
            config=config,
            repo_id=repo_id,
            pull_request_id=pull_request_id,
            thread_id=op.thread_id,
            comment_id=op.comment_id,
            new_content=op.new_content,
            dry_run=dry_run,
        )
        patch_thread_status(
            requests_module=requests_module,
            headers=headers,
            config=config,
            repo_id=repo_id,
            pull_request_id=pull_request_id,
            thread_id=op.thread_id,
            status=op.thread_status,
            dry_run=dry_run,
        )
