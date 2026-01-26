"""
Pure utility functions for PR review workflow.

These functions have no side effects (no state reading, no API calls, no file I/O).
They are easily testable and reusable.
"""

import hashlib
import re
from typing import Dict, List, Optional

# Regex to extract Jira issue keys from PR titles
# Matches patterns like: DFLY-1234, [DFLY-1234], (DFLY-1234), feature(DFLY-1234):
JIRA_ISSUE_KEY_PATTERN = re.compile(r"\b([A-Z]+-\d+)\b")


def extract_jira_issue_key_from_title(title: str) -> Optional[str]:
    """
    Extract Jira issue key from a PR title.

    Looks for patterns like:
    - feature(DFLY-1234): description
    - [DFLY-1234] description
    - fix(DFLY-1234 / DFLY-5678): description (returns first match)

    Args:
        title: Pull request title

    Returns:
        First Jira issue key found, or None
    """
    if not title:
        return None

    matches = JIRA_ISSUE_KEY_PATTERN.findall(title)
    return matches[0] if matches else None


def convert_to_prompt_filename(file_path: str) -> str:
    """
    Convert file path to a unique prompt filename using SHA256 hash.

    Args:
        file_path: Repository file path

    Returns:
        Filename like "file-abc123def456.md"
    """
    if not file_path:
        return "file-metadata-missing.md"

    hash_obj = hashlib.sha256(file_path.encode("utf-8"))
    hash_str = hash_obj.hexdigest()[:16].lower()
    return f"file-{hash_str}.md"


def normalize_repo_path(path: str) -> Optional[str]:
    """
    Normalize a repository path to /path/to/file format.

    Args:
        path: File path (may have backslashes, leading slashes, etc.)

    Returns:
        Normalized path like "/src/app/file.ts" or None if invalid
    """
    if not path or not path.strip():
        return None

    clean = path.strip().replace("\\", "/").strip()
    without_leading = clean.lstrip("/")
    if not without_leading:
        return None
    return f"/{without_leading}"


def get_root_folder(file_path: str) -> str:
    """
    Get the root folder from a file path.

    Args:
        file_path: Repository file path

    Returns:
        Root folder name (e.g., "src") or "root" if no folder
    """
    if not file_path:
        return "root"

    normalized = file_path.replace("\\", "/")
    if "/" not in normalized:
        return "root"
    return normalized.split("/")[0]


def filter_threads(threads: List[Dict]) -> List[Dict]:
    """
    Filter out deleted threads and comments.

    Args:
        threads: List of PR thread dictionaries

    Returns:
        Filtered list with deleted items removed
    """
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

        # Create a copy to avoid mutating the original
        thread_copy = dict(thread)
        thread_copy["comments"] = filtered_comments
        filtered.append(thread_copy)

    return filtered


def get_threads_for_file(threads: List[Dict], file_path: str) -> List[Dict]:
    """
    Get threads that are associated with a specific file.

    Args:
        threads: List of PR thread dictionaries
        file_path: Repository file path to match

    Returns:
        List of threads for the specified file
    """
    if not threads:
        return []

    normalized_path = file_path.replace("\\", "/").lstrip("/")
    matching = []

    for thread in threads:
        if not thread:
            continue

        context = thread.get("threadContext")
        thread_path = None

        if context:
            if context.get("filePath"):
                thread_path = context["filePath"]
            elif context.get("leftFileStart", {}).get("filePath"):
                thread_path = context["leftFileStart"]["filePath"]
            elif context.get("rightFileStart", {}).get("filePath"):
                thread_path = context["rightFileStart"]["filePath"]

        if not thread_path:
            continue

        thread_path = thread_path.replace("\\", "/").lstrip("/")
        if thread_path == normalized_path:
            matching.append(thread)

    return matching


def build_reviewed_paths_set(pr_details: Dict) -> set:
    """
    Build a set of already-reviewed file paths from PR details.

    Args:
        pr_details: Full PR details payload

    Returns:
        Set of lowercase normalized paths that have been reviewed
    """
    reviewed_paths = set()
    reviewer_data = pr_details.get("reviewer", {}) or {}
    reviewed_files = reviewer_data.get("reviewedFiles", []) or []

    for path in reviewed_files:
        normalized = normalize_repo_path(path)
        if normalized:
            reviewed_paths.add(normalized.lower())

    return reviewed_paths
