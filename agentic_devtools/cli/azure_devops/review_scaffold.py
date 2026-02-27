"""Scaffolding for PR review threads.

Creates all summary threads upfront before the agent begins reviewing files.
For a PR with N files across F folders:
  - N file summary threads (anchored to file path, no line)
  - F folder summary threads (PR-level, no file context)
  - 1 overall PR summary thread (PR-level)
Total: N + F + 1 API calls (one-time upfront cost).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .config import AzureDevOpsConfig
from .review_state import (
    FileEntry,
    FolderEntry,
    OverallSummary,
    ReviewState,
    ReviewStatus,
    load_review_state,
    normalize_file_path,
    save_review_state,
)
from .review_templates import render_file_summary, render_folder_summary, render_overall_summary


def _get_folder_for_path(file_path: str) -> str:
    """Get the top-level folder name for a file path.

    Args:
        file_path: Repository file path (with or without leading slash).

    Returns:
        Top-level folder name, or "root" for root-level files.
    """
    from .review_helpers import get_root_folder

    normalized = normalize_file_path(file_path)
    return get_root_folder(normalized.lstrip("/"))


def _get_file_name(file_path: str) -> str:
    """Get the base file name from a file path.

    Args:
        file_path: Repository file path.

    Returns:
        Base file name (last path segment).
    """
    normalized = normalize_file_path(file_path)
    return normalized.split("/")[-1]


def _build_pr_base_url(config: AzureDevOpsConfig, pull_request_id: int) -> str:
    """Build the PR web URL for building discussion links.

    Args:
        config: Azure DevOps configuration.
        pull_request_id: Pull request ID.

    Returns:
        PR web URL string.
    """
    org = config.organization.rstrip("/")
    if not org.startswith(("http://", "https://")):
        org = f"https://dev.azure.com/{org.lstrip('/')}"
    return f"{org}/{config.project}/_git/{config.repository}/pullRequest/{pull_request_id}"


def _post_thread(
    requests_module: Any,
    headers: Dict[str, str],
    threads_url: str,
    content: str,
    file_path: Optional[str] = None,
) -> Tuple[int, int]:
    """Post a PR thread and return (thread_id, comment_id).

    Args:
        requests_module: requests module for HTTP calls.
        headers: Auth headers.
        threads_url: URL to POST threads to.
        content: Thread initial comment content.
        file_path: Optional file path for file-anchored threads (no line context).

    Returns:
        Tuple of (thread_id, comment_id).
    """
    thread_body: Dict[str, Any] = {
        "comments": [
            {
                "content": content,
                "commentType": "text",
            }
        ],
        "status": "active",
    }
    if file_path:
        thread_body["threadContext"] = {"filePath": file_path}

    response = requests_module.post(threads_url, headers=headers, json=thread_body, timeout=30)
    response.raise_for_status()
    result = response.json()
    thread_id = result["id"]
    comment_id = result["comments"][0]["id"]
    return thread_id, comment_id


def _print_dry_run_plan(
    pull_request_id: int,
    files: List[str],
    folders: Dict[str, List[str]],
) -> None:
    """Print the scaffolding plan without making API calls.

    Args:
        pull_request_id: Pull request ID.
        files: List of file paths.
        folders: Mapping of folder name to list of file paths.
    """
    print(f"[DRY RUN] Scaffolding plan for PR {pull_request_id}:")
    for file_path in files:
        normalized = normalize_file_path(file_path)
        print(f"  [DRY RUN] Would create file summary thread for {normalized}")
    for folder_name in folders:
        print(f"  [DRY RUN] Would create folder summary thread for {folder_name}")
    print("  [DRY RUN] Would create overall PR summary thread")
    api_calls = len(files) + len(folders) + 1
    print(f"  [DRY RUN] Total API calls: {api_calls}")


def scaffold_review_threads(
    pull_request_id: int,
    files: List[str],
    config: AzureDevOpsConfig,
    repo_id: str,
    repo_name: str,
    latest_iteration_id: int,
    requests_module: Any,
    headers: Dict[str, str],
    dry_run: bool = False,
) -> Optional[ReviewState]:
    """Create all summary threads upfront before reviewing files.

    For a PR with N files across F folders, creates:
      - N file summary threads (anchored to file path, no line)
      - F folder summary threads (PR-level, no file context)
      - 1 overall PR summary thread (PR-level, links to folder threads)

    Idempotent: if review-state.json already exists for the PR, skips creation
    and returns the existing state.

    Args:
        pull_request_id: PR ID.
        files: List of file paths to scaffold threads for.
        config: Azure DevOps configuration.
        repo_id: Repository ID (GUID).
        repo_name: Repository name.
        latest_iteration_id: Latest iteration ID for the PR.
        requests_module: Injected requests module (for testability).
        headers: Auth headers dict.
        dry_run: If True, print the plan without making API calls.

    Returns:
        ReviewState with all thread IDs saved.  Returns the existing state
        if scaffolding was already completed (idempotency check runs first).
        Returns None only when ``dry_run=True`` *and* no prior scaffolding exists.
    """
    # Idempotency check: skip if review-state.json already exists
    try:
        existing_state = load_review_state(pull_request_id)
        print(f"Scaffolding already exists for PR {pull_request_id}. Skipping.")
        return existing_state
    except FileNotFoundError:
        pass

    # Group files by top-level folder
    folders: Dict[str, List[str]] = {}
    for file_path in files:
        folder = _get_folder_for_path(file_path)
        normalized = normalize_file_path(file_path)
        folders.setdefault(folder, []).append(normalized)

    if dry_run:
        _print_dry_run_plan(pull_request_id, files, folders)
        return None

    threads_url = config.build_api_url(repo_id, "pullRequests", pull_request_id, "threads")
    base_url = _build_pr_base_url(config, pull_request_id)
    scaffolded_utc = datetime.now(timezone.utc).isoformat()

    # Step 1: Create file summary threads (anchored to file path, no line)
    file_entries: Dict[str, FileEntry] = {}
    for file_path in files:
        normalized = normalize_file_path(file_path)
        folder = _get_folder_for_path(file_path)
        file_name = _get_file_name(file_path)

        temp_entry = FileEntry(
            threadId=0,
            commentId=0,
            folder=folder,
            fileName=file_name,
            status=ReviewStatus.UNREVIEWED.value,
        )
        content = render_file_summary(temp_entry, [], base_url)

        print(f"Creating file summary thread for {normalized}...")
        thread_id, comment_id = _post_thread(requests_module, headers, threads_url, content, file_path=normalized)
        file_entries[normalized] = FileEntry(
            threadId=thread_id,
            commentId=comment_id,
            folder=folder,
            fileName=file_name,
            status=ReviewStatus.UNREVIEWED.value,
        )

    # Step 2: Create folder summary threads (PR-level, no file context)
    folder_entries: Dict[str, FolderEntry] = {}
    for folder_name, folder_files in folders.items():
        temp_folder = FolderEntry(
            threadId=0,
            commentId=0,
            status=ReviewStatus.UNREVIEWED.value,
            files=folder_files,
        )
        content = render_folder_summary(folder_name, temp_folder, file_entries, base_url)

        print(f"Creating folder summary thread for {folder_name}...")
        thread_id, comment_id = _post_thread(requests_module, headers, threads_url, content)
        folder_entries[folder_name] = FolderEntry(
            threadId=thread_id,
            commentId=comment_id,
            status=ReviewStatus.UNREVIEWED.value,
            files=folder_files,
        )

    # Step 3: Create overall PR summary thread (PR-level, links to folder threads)
    temp_state = ReviewState(
        prId=pull_request_id,
        repoId=repo_id,
        repoName=repo_name,
        project=config.project,
        organization=config.organization,
        latestIterationId=latest_iteration_id,
        scaffoldedUtc=scaffolded_utc,
        overallSummary=OverallSummary(threadId=0, commentId=0),
        folders=folder_entries,
        files=file_entries,
    )
    overall_content = render_overall_summary(temp_state, base_url)

    print("Creating overall PR summary thread...")
    overall_thread_id, overall_comment_id = _post_thread(requests_module, headers, threads_url, overall_content)

    # Build final ReviewState and persist
    review_state = ReviewState(
        prId=pull_request_id,
        repoId=repo_id,
        repoName=repo_name,
        project=config.project,
        organization=config.organization,
        latestIterationId=latest_iteration_id,
        scaffoldedUtc=scaffolded_utc,
        overallSummary=OverallSummary(threadId=overall_thread_id, commentId=overall_comment_id),
        folders=folder_entries,
        files=file_entries,
    )

    save_review_state(review_state)
    print(f"Scaffolding complete. Review state saved for PR {pull_request_id}.")

    return review_state
