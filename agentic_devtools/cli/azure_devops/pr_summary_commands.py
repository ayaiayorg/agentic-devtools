"""
Pull Request Summary Commands.

Generates overarching PR review comments after all files have been reviewed.
This mirrors the generate-overarching-pr-comments.ps1 functionality.

.. deprecated::
    This module is deprecated. PR summaries are now generated automatically
    during agdt-review-pull-request scaffolding.
"""

import json
import sys
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ...state import get_pull_request_id, is_dry_run, set_value
from .auth import get_auth_headers, get_pat
from .config import APPROVAL_SENTINEL, AzureDevOpsConfig
from .helpers import get_repository_id, require_requests


@dataclass
class FileSummary:
    """Summary of a file's review status."""

    normalized_path: str
    path: str
    root_folder: str
    threads: List[Dict]
    status: str  # 'Approved' or 'NeedsWork'


@dataclass
class FolderSummary:
    """Summary of a folder's review status."""

    name: str
    status: str
    thread_id: Optional[int] = None
    comment_id: Optional[int] = None
    comment_url: Optional[str] = None


def _normalize_repo_path(path: Optional[str]) -> Optional[str]:
    """Normalize a file path to repository format (/path/to/file)."""
    if not path or not path.strip():
        return None
    clean = path.strip().replace("\\", "/").strip("/")
    if not clean:
        return None
    return f"/{clean}"


def _get_root_folder(file_path: str) -> str:
    """Get the root folder from a file path."""
    if not file_path:
        return "root"
    normalized = file_path.replace("\\", "/")
    if "/" not in normalized:
        return "root"
    return normalized.split("/")[0]


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


def _filter_threads(threads: List[Dict]) -> List[Dict]:
    """Filter out deleted threads and comments."""
    if not threads:
        return []

    filtered = []
    for thread in threads:
        if not thread:
            continue
        if thread.get("isDeleted"):
            continue

        comments = thread.get("comments", [])
        filtered_comments = [c for c in comments if c and not c.get("isDeleted")]

        if not filtered_comments:
            continue

        thread_copy = dict(thread)
        thread_copy["comments"] = filtered_comments
        filtered.append(thread_copy)

    return filtered


def _get_file_thread_status(threads: List[Dict]) -> str:
    """Determine if file needs work based on thread status."""
    for thread in threads:
        status = thread.get("status")
        if status in ("active", "pending"):
            return "NeedsWork"
    return "Approved"


def _get_azure_devops_sort_key(path: str) -> str:
    """Get sort key for Azure DevOps file ordering."""
    if not path:
        return "1|"

    normalized = path.lstrip("/")
    if not normalized:
        return "1|"

    segments = normalized.split("/")
    if not segments:  # pragma: no cover
        return "1|"

    result = ""
    for i, segment in enumerate(segments):
        is_last = i == len(segments) - 1
        type_indicator = "1" if is_last else "0"
        result += f"{type_indicator}|{segment.lower()}|"

    return result


def _sort_entries_by_path(entries: List[FileSummary]) -> List[FileSummary]:
    """Sort file entries by Azure DevOps path ordering."""
    return sorted(entries, key=lambda e: _get_azure_devops_sort_key(e.path))


def _sort_folders(folders: List[FolderSummary]) -> List[FolderSummary]:
    """Sort folder summaries (root last, then alphabetically)."""
    return sorted(
        folders,
        key=lambda f: (1 if f.name.lower() == "root" else 0, f.name.lower()),
    )


def _build_comment_link(
    config: AzureDevOpsConfig,
    pull_request_id: int,
    thread_id: Optional[int] = None,
    comment_id: Optional[int] = None,
) -> str:
    """Build a link to a PR comment."""
    base = config.organization.rstrip("/")
    encoded_project = urllib.parse.quote(config.project, safe="")
    encoded_repo = urllib.parse.quote(config.repository, safe="")
    pr_root = f"{base}/{encoded_project}/_git/{encoded_repo}/pullRequest/{pull_request_id}"

    if thread_id and comment_id:
        url = f"{pr_root}?discussionId={thread_id}&commentId={comment_id}"
    elif thread_id:
        url = f"{pr_root}?discussionId={thread_id}"
    elif comment_id:
        url = f"{pr_root}#{comment_id}"
    else:
        url = pr_root

    # Escape ampersands for markdown
    return url.replace("&", "&amp;")


def _get_latest_comment_context(threads: List[Dict]) -> Optional[Tuple[Dict, Optional[Dict]]]:
    """Get the most recently updated thread and comment."""
    if not threads:
        return None

    candidates = []

    for thread in threads:
        if not thread:
            continue

        comments = thread.get("comments", [])
        if comments:
            for comment in comments:
                if not comment:
                    continue
                if comment.get("commentType") == "codePosition":
                    continue

                timestamp_str = (
                    comment.get("lastUpdatedDate")
                    or comment.get("lastContentUpdatedDate")
                    or comment.get("publishedDate")
                )

                timestamp = datetime.min.replace(tzinfo=timezone.utc)
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    except ValueError:
                        pass

                candidates.append((timestamp, thread, comment))
        else:
            timestamp_str = thread.get("lastUpdatedDate") or thread.get("publishedDate")

            timestamp = datetime.min.replace(tzinfo=timezone.utc)
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except ValueError:  # pragma: no cover
                    pass

            candidates.append((timestamp, thread, None))

    if not candidates:  # pragma: no cover
        return None

    # Sort by timestamp descending and get the latest
    candidates.sort(key=lambda x: x[0], reverse=True)
    _, thread, comment = candidates[0]
    return (thread, comment)


def _build_file_link(
    file_path: str,
    threads: List[Dict],
    config: AzureDevOpsConfig,
    pull_request_id: int,
) -> str:
    """Build a markdown link to a file's comment thread."""
    display_path = file_path
    if not display_path:
        display_path = "root"
    elif not display_path.startswith("/"):  # pragma: no cover
        display_path = f"/{display_path.lstrip('/')}"

    context = _get_latest_comment_context(threads)
    if not context:  # pragma: no cover
        # Try first thread with first comment
        if threads:
            thread = threads[0]
            comments = thread.get("comments", [])
            comment = None
            if comments:
                for c in comments:
                    if c.get("commentType") != "codePosition":
                        comment = c
                        break
                if not comment:
                    comment = comments[0] if comments else None
            context = (thread, comment)

    if not context:
        return display_path

    thread, comment = context
    thread_id = thread.get("id")
    comment_id = comment.get("id") if comment else None

    if not thread_id:
        return display_path

    link = _build_comment_link(config, pull_request_id, thread_id, comment_id)
    return f"[{display_path}]({link})"


def _build_folder_comment(
    folder_name: str,
    file_summaries: List[FileSummary],
    config: AzureDevOpsConfig,
    pull_request_id: int,
) -> Tuple[str, str]:
    """Build a folder summary comment body."""
    needs_work = [f for f in file_summaries if f.status == "NeedsWork"]
    approved = [f for f in file_summaries if f.status == "Approved"]

    needs_work_sorted = _sort_entries_by_path(needs_work)
    approved_sorted = _sort_entries_by_path(approved)

    status = "Needs Work" if needs_work else "Approved"

    lines = [
        f"## Folder Review Summary: {folder_name}",
        "",
        f"*Status:* {status}",
    ]

    if needs_work_sorted:
        lines.extend(["", "### Needs Work"])
        for entry in needs_work_sorted:
            file_link = _build_file_link(entry.path, entry.threads, config, pull_request_id)
            lines.append(f"- {file_link}")

    if approved_sorted:
        lines.extend(["", "### Approved"])
        for entry in approved_sorted:
            file_link = _build_file_link(entry.path, entry.threads, config, pull_request_id)
            lines.append(f"- {file_link}")

    return "\n".join(lines), status


def _post_comment(
    requests,
    headers: Dict,
    config: AzureDevOpsConfig,
    repo_id: str,
    pull_request_id: int,
    content: str,
    leave_active: bool = False,
) -> Optional[Dict[str, Any]]:
    """Post a comment to the PR and optionally resolve it."""
    thread_url = config.build_api_url(repo_id, "pullRequests", pull_request_id, "threads")

    # Wrap with approval sentinel banner
    formatted_content = f"{APPROVAL_SENTINEL}\n\n{content.strip()}\n\n{APPROVAL_SENTINEL}\n\n"

    thread_body = {
        "comments": [{"content": formatted_content, "commentType": "text"}],
        "status": "active",
    }

    try:
        response = requests.post(thread_url, headers=headers, json=thread_body, timeout=30)
        response.raise_for_status()
        result = response.json()
    except Exception as e:
        print(f"Warning: Failed to post comment: {e}", file=sys.stderr)
        return None

    thread_id = result.get("id")
    comments = result.get("comments", [])
    comment_id = comments[0].get("id") if comments else None

    # Resolve thread unless leave_active
    if not leave_active and thread_id:
        try:
            resolve_url = config.build_api_url(repo_id, "pullRequests", pull_request_id, "threads", thread_id)
            requests.patch(resolve_url, headers=headers, json={"status": "closed"}, timeout=30)
        except Exception as e:
            print(f"Warning: Failed to resolve thread {thread_id}: {e}", file=sys.stderr)

    return {"thread_id": thread_id, "comment_id": comment_id}


def generate_overarching_pr_comments() -> bool:  # pragma: no cover
    """
    Generate overarching review comments for each folder and overall PR summary.

    This function:
    1. Fetches PR details (files and threads)
    2. Groups files by root folder
    3. Posts a summary comment for each folder
    4. Posts an overall PR summary with links to folder summaries

    State keys read:
        - pull_request_id (required): Pull request ID
        - dry_run: If true, only print what would be done

    Returns:
        True if summary comments were generated successfully (or nothing to do),
        False if an error occurred.
    """
    requests = require_requests()
    config = AzureDevOpsConfig.from_state()
    dry_run = is_dry_run()
    pull_request_id = get_pull_request_id(required=True)

    print(f"Generating overarching review comments for PR {pull_request_id}")
    print("=" * 59)
    print("")

    # Step 1: Fetch PR details
    from .pull_request_details_commands import get_pull_request_details

    set_value("pull_request_id", pull_request_id)
    get_pull_request_details()

    # Load details from temp file
    scripts_dir = Path(__file__).parent.parent.parent.parent.parent
    temp_dir = scripts_dir / "temp"
    details_path = temp_dir / "temp-get-pull-request-details-response.json"

    if not details_path.exists():
        print("ERROR: PR details file not found after fetch.", file=sys.stderr)
        sys.exit(1)

    with open(details_path, encoding="utf-8") as f:
        pr_details = json.load(f)

    if pr_details.get("error"):
        print(f"Failed to retrieve PR details: {pr_details['error']}", file=sys.stderr)
        sys.exit(1)

    # Extract files and threads
    files_payload = pr_details.get("files", [])
    if not files_payload:
        print("No file metadata found in PR details; nothing to summarize.")
        return True  # Nothing to do is a successful state

    threads_payload = pr_details.get("threads", [])
    if not threads_payload:
        print("No discussion threads detected. Skipping overarching comments.")
        return True  # Nothing to do is a successful state

    threads_payload = _filter_threads(threads_payload)
    if not threads_payload:
        print("No discussion threads detected after filtering. Skipping overarching comments.")
        return True  # Nothing to do is a successful state

    # Step 2: Build map of files to threads
    files_by_path: Dict[str, List[Dict]] = {}
    for thread in threads_payload:
        file_path = _get_thread_file_path(thread)
        if not file_path:
            continue

        normalized = _normalize_repo_path(file_path)
        if not normalized:
            continue

        if normalized not in files_by_path:
            files_by_path[normalized] = []
        files_by_path[normalized].append(thread)

    if not files_by_path:
        print("No file-scoped threads detected. Overarching comments are not required.")
        return True  # Nothing to do is a successful state

    # Step 3: Build file summaries
    file_summaries: List[FileSummary] = []

    # Process in file order from the PR
    ordered_paths: List[str] = []
    for file_detail in files_payload:
        if not file_detail:
            continue
        for candidate_key in ("path", "originalPath"):
            candidate = file_detail.get(candidate_key)
            if candidate:
                normalized = _normalize_repo_path(candidate)
                if normalized and normalized in files_by_path and normalized not in ordered_paths:
                    ordered_paths.append(normalized)

    # Add any remaining paths not in file list
    for path in files_by_path:
        if path not in ordered_paths:
            ordered_paths.append(path)

    for normalized_path in ordered_paths:
        threads_for_file = files_by_path.get(normalized_path, [])
        if not threads_for_file:
            continue

        # Find matching file detail
        matching_file = None
        for f in files_payload:
            if f:
                f_normalized = _normalize_repo_path(f.get("path"))
                orig_normalized = _normalize_repo_path(f.get("originalPath"))
                if f_normalized == normalized_path or orig_normalized == normalized_path:
                    matching_file = f
                    break

        if not matching_file:
            continue

        original_path = matching_file.get("path") or matching_file.get("originalPath") or normalized_path.lstrip("/")
        root_folder = _get_root_folder(original_path)
        status = _get_file_thread_status(threads_for_file)

        file_summaries.append(
            FileSummary(
                normalized_path=normalized_path,
                path=original_path,
                root_folder=root_folder,
                threads=threads_for_file,
                status=status,
            )
        )

    if not file_summaries:
        print("No file summaries produced; nothing to post.")
        return True  # Nothing to do is a successful state

    # Step 4: Group by folder and post comments
    if not dry_run:
        pat = get_pat()
        headers = get_auth_headers(pat)
        repo_id = get_repository_id(config.organization, config.project, config.repository)

    # Group by root folder
    folders_map: Dict[str, List[FileSummary]] = {}
    for summary in file_summaries:
        folder = summary.root_folder
        if folder not in folders_map:
            folders_map[folder] = []
        folders_map[folder].append(summary)

    folder_results: List[FolderSummary] = []

    for folder_name, folder_files in folders_map.items():
        comment_body, folder_status = _build_folder_comment(folder_name, folder_files, config, pull_request_id)

        print(f"Preparing summary for folder '{folder_name}' (Status: {folder_status}).")

        if dry_run:
            print(comment_body)
            folder_results.append(FolderSummary(name=folder_name, status=folder_status))
            continue

        leave_active = folder_status == "Needs Work"
        result = _post_comment(requests, headers, config, repo_id, pull_request_id, comment_body, leave_active)

        link = None
        if result and result.get("thread_id"):
            link = _build_comment_link(config, pull_request_id, result["thread_id"], result.get("comment_id"))

        folder_results.append(
            FolderSummary(
                name=folder_name,
                status=folder_status,
                thread_id=result.get("thread_id") if result else None,
                comment_id=result.get("comment_id") if result else None,
                comment_url=link,
            )
        )

    if dry_run:
        print("Dry run complete – no comments were posted.")
        return True  # Dry run completed successfully

    # Step 5: Post overall PR summary
    needs_work_folders = [f for f in folder_results if f.status == "Needs Work"]
    approved_folders = [f for f in folder_results if f.status == "Approved"]
    final_status = "Needs Work" if needs_work_folders else "Approved"

    sorted_needs_work = _sort_folders(needs_work_folders)
    sorted_approved = _sort_folders(approved_folders)

    lines = [
        "## Overall PR Review Summary",
        "",
        f"*Status:* {final_status}",
    ]

    if sorted_needs_work:
        lines.extend(["", "### Folders Needing Work"])
        for folder in sorted_needs_work:
            label = f"[{folder.name}]({folder.comment_url})" if folder.comment_url else folder.name
            lines.append(f"- {label}")

    if sorted_approved:
        lines.extend(["", "### Approved Folders"])
        for folder in sorted_approved:
            label = f"[{folder.name}]({folder.comment_url})" if folder.comment_url else folder.name
            lines.append(f"- {label}")

    final_comment = "\n".join(lines)

    leave_active = final_status == "Needs Work"
    _post_comment(requests, headers, config, repo_id, pull_request_id, final_comment, leave_active)

    if final_status == "Approved":
        print("Posted final PR summary (approved).")
    else:
        print("Posted final PR summary (needs work).")

    return True  # Successfully posted summary comments


def generate_overarching_pr_comments_cli() -> None:
    """
    CLI entry point for generate_overarching_pr_comments.

    .. deprecated::
        This command is deprecated. PR summaries are now generated automatically
        during agdt-review-pull-request scaffolding. The deprecation warning is
        emitted by the user-facing wrapper (generate_pr_summary_async), not here,
        because this function is also invoked as a background entry point by the
        automated review workflow.
    """
    generate_overarching_pr_comments()
