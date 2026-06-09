"""Scaffolding for PR review threads.

Creates all summary threads upfront before the agent begins reviewing files.
For a PR with N files:
  - N file summary threads (anchored to file path, no line)
  - 1 overall PR summary thread (PR-level)
  - 1 Review Activity Log thread (PR-level, no file context)
Total: N + 3 API calls (one-time upfront cost).

Folder-level threads have been eliminated; folders are now lightweight
groupings within the overall PR summary comment.

Session management, commit-hash-based idempotency, and incremental
re-scaffolding are also handled here.
"""

import sys
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from .config import AzureDevOpsConfig
from .helpers import build_cross_identity_reply_content, patch_thread_status
from .marker import build_marker
from .review_attribution import build_commit_file_url, build_commit_pr_url
from .review_state import (
    FileEntry,
    FolderGroup,
    ModelVerdict,
    OverallSummary,
    ReviewSession,
    ReviewState,
    ReviewStatus,
    load_review_state,
    normalize_file_path,
    save_review_state,
)
from .review_templates import render_file_summary, render_overall_summary, rewrite_header_for_subsequent
from .suggestion_verification import (
    categorize_all_suggestions,
    fetch_threads_lookup,
    has_unaddressed,
    partition_results,
    render_abort_summary,
    render_unaddressed_thread_comment,
)
from .verdict_protocol import initialize_model_verdicts

# Stale session threshold: sessions older than this are considered crashed.
STALE_SESSION_THRESHOLD = timedelta(hours=2)


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


def build_pr_base_url(config: AzureDevOpsConfig, pull_request_id: int) -> str:
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
    encoded_project = quote(config.project, safe="")
    encoded_repo = quote(config.repository, safe="")
    return f"{org}/{encoded_project}/_git/{encoded_repo}/pullrequest/{pull_request_id}"


# Backward-compatible alias for internal callers
_build_pr_base_url = build_pr_base_url


def _post_thread(
    requests_module: Any,
    headers: dict[str, str],
    threads_url: str,
    content: str,
    file_path: str | None = None,
    marker: str | None = None,
) -> tuple[int, int]:
    """Post a PR thread and return (thread_id, comment_id).

    Args:
        requests_module: requests module for HTTP calls.
        headers: Auth headers.
        threads_url: URL to POST threads to.
        content: Thread initial comment content.
        file_path: Optional file path for file-anchored threads (no line context).
        marker: Optional HTML comment marker to prepend to content.

    Returns:
        Tuple of (thread_id, comment_id).
    """
    if marker is not None:
        content = f"{marker}\n{content}"

    thread_body: dict[str, Any] = {
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


# ---------------------------------------------------------------------------
# FileChangeResult — differential file detection result
# ---------------------------------------------------------------------------


@dataclass
class FileChangeResult:
    """Result of differential file detection between two commits.

    Categorises every file in the PR as new, modified, deleted, or unchanged
    relative to a previous scaffolding run.
    """

    new_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    deleted_files: list[str] = field(default_factory=list)
    unchanged_files: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Reply / demotion helpers
# ---------------------------------------------------------------------------


def _append_path_to_url(base_url: str, *segments: str | int) -> str:
    """Append path segments to a URL, preserving any query string.

    If ``base_url`` contains a query string (e.g. ``?api-version=7.0``),
    the new segments are inserted before it.  Trailing/leading slashes are
    normalised to avoid double-slash artifacts.

    Args:
        base_url: The base URL (may include a query string).
        *segments: Path segments to append (converted to str).

    Returns:
        URL with segments appended before the query string, or the
        original *base_url* unchanged when no segments are provided.
    """
    if not segments:
        return base_url

    if "?" in base_url:
        path_part, query_part = base_url.split("?", 1)
    else:
        path_part, query_part = base_url, None

    normalized_base = path_part.rstrip("/")
    suffix = "/".join(str(s).strip("/") for s in segments)

    new_path = f"{normalized_base}/{suffix}" if suffix else normalized_base

    if query_part is not None:
        return f"{new_path}?{query_part}"
    return new_path


def _post_reply(
    requests_module: Any,
    headers: dict[str, str],
    threads_url: str,
    thread_id: int,
    content: str,
) -> int:
    """Post a reply to an existing thread.

    Args:
        requests_module: requests module for HTTP calls.
        headers: Auth headers.
        threads_url: Base threads URL (without thread ID suffix).
        thread_id: Thread to reply to.
        content: Reply content (markdown).

    Returns:
        The new comment ID.
    """
    url = _append_path_to_url(threads_url, thread_id, "comments")
    body = {"content": content, "commentType": "text"}
    response = requests_module.post(url, headers=headers, json=body, timeout=30)
    response.raise_for_status()
    return response.json()["id"]


def _post_cross_identity_reply(
    requests_module: Any,
    headers: dict[str, str],
    threads_url: str,
    thread_id: int,
    content: str,
) -> int:
    """Post a cross-identity update reply to an existing thread.

    Used when the original thread comment is owned by a different identity
    and cannot be PATCHed. Posts the full content as a reply prefixed with
    a cross-identity-update marker.

    Args:
        requests_module: requests module for HTTP calls.
        headers: Auth headers.
        threads_url: Base threads URL.
        thread_id: Thread to reply to.
        content: Full scaffold content to post.

    Returns:
        The new reply comment ID.
    """
    return _post_reply(requests_module, headers, threads_url, thread_id, build_cross_identity_reply_content(content))


def _get_thread_comments(
    requests_module: Any,
    headers: dict[str, str],
    threads_url: str,
    thread_id: int,
) -> list[dict[str, Any]]:
    """GET a thread and return its comments list.

    Args:
        requests_module: requests module for HTTP calls.
        headers: Auth headers.
        threads_url: Base threads URL.
        thread_id: Thread to fetch.

    Returns:
        List of comment dicts from the API response.
    """
    url = _append_path_to_url(threads_url, thread_id)
    response = requests_module.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json().get("comments", [])


def _patch_comment_content(
    requests_module: Any,
    headers: dict[str, str],
    threads_url: str,
    thread_id: int,
    comment_id: int,
    new_content: str,
    cross_identity: bool = False,
) -> None:
    """PATCH a single comment's content, falling back to reply on 403.

    When ``cross_identity`` is True or a 403 is received, posts the content
    as a reply to the thread instead of editing the original comment.

    Args:
        requests_module: requests module for HTTP calls.
        headers: Auth headers.
        threads_url: Base threads URL.
        thread_id: Thread containing the comment.
        comment_id: Comment to update.
        new_content: New markdown content.
        cross_identity: If True, skip PATCH and post reply directly.
    """
    if cross_identity:
        _post_cross_identity_reply(requests_module, headers, threads_url, thread_id, new_content)
        return

    url = _append_path_to_url(threads_url, thread_id, "comments", comment_id)
    response = requests_module.patch(url, headers=headers, json={"content": new_content}, timeout=30)
    if response.status_code == 403:
        # Cross-identity ownership — fall back to reply
        _post_cross_identity_reply(requests_module, headers, threads_url, thread_id, new_content)
        return
    response.raise_for_status()


def _demote_main_comment(
    requests_module: Any,
    headers: dict[str, str],
    threads_url: str,
    thread_id: int,
    comment_id: int,
    new_main_content: str,
    commit_hash: str | None = None,
    commit_url: str | None = None,
) -> int:
    """Read current main comment, post it as reply, PATCH main with new content.

    Steps:
      1. GET the thread to read current main comment content.
      2. POST current content as a reply (preserving it as history).
         The reply header is rewritten from ``## ... Summary`` to
         ``### Commit: ...`` using ``rewrite_header_for_subsequent()``.
      3. PATCH the main comment with ``new_main_content``.

    Args:
        requests_module: requests module for HTTP calls.
        headers: Auth headers.
        threads_url: Base threads URL.
        thread_id: Thread whose main comment is being demoted.
        comment_id: The main comment ID (usually 1).
        new_main_content: New content for the main comment.
        commit_hash: Commit hash for the reply header. When provided,
            the demoted reply uses a compact commit-scoped heading.
        commit_url: Commit URL for the reply header link.

    Returns:
        The comment ID of the newly-created reply (the demoted content).
    """
    # Step 1: Read current main comment content
    comments = _get_thread_comments(requests_module, headers, threads_url, thread_id)
    old_content = ""
    for comment in comments:
        if comment.get("id") == comment_id:
            old_content = comment.get("content", "")
            break

    # Step 2: Post old content as a reply (with header rewritten for subsequent format)
    reply_content = rewrite_header_for_subsequent(old_content, commit_hash, commit_url)
    reply_id = _post_reply(requests_module, headers, threads_url, thread_id, reply_content)

    # Step 3: PATCH main comment with new content
    _patch_comment_content(requests_module, headers, threads_url, thread_id, comment_id, new_main_content)

    return reply_id


# ---------------------------------------------------------------------------
# Activity log helpers
# ---------------------------------------------------------------------------


def _format_activity_log_entry(
    status_emoji: str,
    status_text: str,
    timestamp: str,
    model_name: str,
    short_hash: str,
    session_id: str,
    detail_message: str,
    sequence_number: int,
) -> str:
    """Format an activity log entry.

    Args:
        status_emoji: Emoji for the status (e.g. "🆕", "⚠️").
        status_text: Status text (e.g. "New Review", "Already Reviewed").
        timestamp: ISO 8601 UTC timestamp.
        model_name: AI model name.
        short_hash: Short commit hash (first 7 characters).
        session_id: Session UUID.
        detail_message: Detail message body.
        sequence_number: Incrementing sequence number for ordering.

    Returns:
        Formatted markdown string.
    """
    return (
        f"{build_marker('activity-log-entry')}\n"
        f"### Review Session — {status_emoji} {status_text}\n"
        f"\n"
        f"*Logged at:* {timestamp}\n"
        f"*Model:* **{model_name}**\n"
        f"*Commit:* `{short_hash}`\n"
        f"*Session ID:* `{session_id}`\n"
        f"\n"
        f"{detail_message}\n"
        f"\n"
        f"<!-- activity-seq:{sequence_number} -->\n"
    )


def _post_activity_log_entry(
    requests_module: Any,
    headers: dict[str, str],
    threads_url: str,
    thread_id: int,
    entry_content: str,
) -> int:
    """Post a new activity log entry as a reply to the activity log thread.

    The header comment ("Review Activity Log") remains pinned as the main
    (top-level) comment.  New entries are posted as replies.

    Args:
        requests_module: requests module for HTTP calls.
        headers: Auth headers.
        threads_url: Base threads URL.
        thread_id: Activity log thread ID.
        entry_content: Formatted markdown for the new entry.

    Returns:
        The comment ID of the newly-created reply.
    """
    return _post_reply(requests_module, headers, threads_url, thread_id, entry_content)


def _update_activity_log_comment_status(
    requests_module: Any,
    headers: dict[str, str],
    threads_url: str,
    thread_id: int,
    comment_id: int,
    status_emoji: str,
    status_text: str,
    session: "ReviewSession",
    commit_hash: str | None,
    sequence_number: int,
    detail_message: str,
) -> None:
    """Update an existing activity log comment to reflect a terminal status.

    Re-renders the entry via ``_format_activity_log_entry`` with the terminal
    status emoji/text and PATCHes the comment in-place.

    Args:
        requests_module: requests module for HTTP calls.
        headers: Auth headers.
        threads_url: Base threads URL.
        thread_id: Activity log thread ID.
        comment_id: Comment ID of the activity log reply to update.
        status_emoji: Emoji for the terminal status (e.g. "\u2705", "\u274c").
        status_text: Status text (e.g. "Completed", "Failed").
        session: The ReviewSession whose entry is being updated.
        commit_hash: Commit hash for display.
        sequence_number: Original sequence number of the entry.
        detail_message: Updated detail message body.
    """
    short_hash = (commit_hash or "unknown")[:7]
    updated_content = _format_activity_log_entry(
        status_emoji,
        status_text,
        session.startedUtc,
        session.modelId,
        short_hash,
        session.sessionId,
        detail_message,
        sequence_number,
    )
    _patch_comment_content(requests_module, headers, threads_url, thread_id, comment_id, updated_content)


# ---------------------------------------------------------------------------
# Session management helpers
# ---------------------------------------------------------------------------


def _check_session_status(
    existing_state: ReviewState,
    commit_hash: str | None,
    model_id: str,
    now: datetime | None = None,
) -> str:
    """Determine the review session status for a given commit + model.

    Args:
        existing_state: Current review state.
        commit_hash: Current commit hash (may be None).
        model_id: Current model identifier.
        now: Current time (injectable for testing).

    Returns:
        One of: "first_review", "already_reviewed", "in_progress",
        "resume_stale", "different_model", "different_commit".
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Normalise None → "" for comparison so that two unknown hashes match.
    effective_old = existing_state.commitHash or ""
    effective_new = commit_hash or ""

    if effective_old == effective_new:
        # Filter by both model and commit hash — sessions accumulate across
        # commits, so we must scope to the current commit to avoid false
        # "already_reviewed" from sessions recorded for prior commits.
        current_hash = commit_hash or ""
        matching_sessions = [
            s for s in existing_state.sessions if s.modelId == model_id and (s.commitHash or "") == current_hash
        ]

        # First, prefer any completed session regardless of insertion order.
        for session in matching_sessions:
            if session.status == "completed":
                return "already_reviewed"

        # No completed session; next, look for in-progress sessions.
        has_stale_in_progress = False
        for session in matching_sessions:
            if session.status == "in_progress":
                started = datetime.fromisoformat(session.startedUtc)
                if now - started < STALE_SESSION_THRESHOLD:
                    return "in_progress"
                has_stale_in_progress = True

        if has_stale_in_progress:
            return "resume_stale"

        # No active/completed sessions for this model — check if a different
        # model has sessions *for the current commit*.  Sessions accumulate across
        # commits (audit trail), so we must scope this check to avoid false
        # positives from sessions created for prior commits.
        if any(s.modelId != model_id and (s.commitHash or "") == current_hash for s in existing_state.sessions):
            return "different_model"
        return "first_review"

    # Different commit hash — handled by caller (incremental re-scaffolding)
    return "different_commit"


def _mark_stale_sessions_failed(
    existing_state: ReviewState,
    commit_hash: str,
    model_id: str,
    now: datetime | None = None,
) -> list[ReviewSession]:
    """Mark all stale in-progress sessions as failed for a commit + model.

    Args:
        existing_state: Review state (mutated in-place).
        commit_hash: Current commit hash.
        model_id: Current model identifier.
        now: Current time (injectable for testing).

    Returns:
        Sessions that were transitioned from in_progress to failed.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    transitioned: list[ReviewSession] = []
    for session in existing_state.sessions:
        if (
            session.modelId == model_id
            and session.status == "in_progress"
            and (session.commitHash or "") == (commit_hash or "")
        ):
            started = datetime.fromisoformat(session.startedUtc)
            if now - started >= STALE_SESSION_THRESHOLD:
                session.status = "failed"
                session.completedUtc = now.isoformat()
                transitioned.append(session)
    return transitioned


def _create_session(
    model_id: str,
    commit_hash: str | None = None,
    now: datetime | None = None,
) -> ReviewSession:
    """Create a new ReviewSession with in_progress status.

    Args:
        model_id: AI model identifier.
        commit_hash: Commit hash this session is reviewing.
        now: Current time (injectable for testing).

    Returns:
        A new ReviewSession.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    return ReviewSession(
        sessionId=uuid.uuid4().hex,
        modelId=model_id,
        startedUtc=now.isoformat(),
        status="in_progress",
        commitHash=commit_hash,
    )


# ---------------------------------------------------------------------------
# Differential file detection
# ---------------------------------------------------------------------------


def detect_file_changes(
    existing_state: ReviewState,
    current_files: list[str],
    config: AzureDevOpsConfig,
    repo_id: str,
    pull_request_id: int,
    old_commit_hash: str,
    new_commit_hash: str,
    requests_module: Any,
    headers: dict[str, str],
) -> FileChangeResult:
    """Detect file changes between two commits for incremental re-scaffolding.

    Primary detection uses the Azure DevOps iterations API. Secondary
    validation uses local ``git diff`` when available.

    Args:
        existing_state: Previous review state.
        current_files: File paths in the new iteration (normalised).
        config: Azure DevOps configuration.
        repo_id: Repository ID (GUID).
        pull_request_id: PR ID.
        old_commit_hash: Previous commit hash.
        new_commit_hash: New commit hash.
        requests_module: requests module for HTTP calls.
        headers: Auth headers.

    Returns:
        FileChangeResult categorising every file.
    """
    existing_file_set = set(existing_state.files.keys())
    current_file_set = {normalize_file_path(f) for f in current_files}

    # Get iteration changes from Azure DevOps
    iteration_changed_files: set = set()
    try:
        # Get latest iteration
        iterations_url = config.build_api_url(repo_id, "pullRequests", pull_request_id, "iterations")
        resp = requests_module.get(iterations_url, headers=headers, timeout=30)
        resp.raise_for_status()
        iterations = resp.json().get("value", [])
        if iterations:
            latest_iteration_id = max(it.get("id", 0) for it in iterations)
            # Get iteration changes
            changes_url = config.build_api_url(
                repo_id, "pullRequests", pull_request_id, "iterations", latest_iteration_id, "changes"
            )
            changes_resp = requests_module.get(changes_url, headers=headers, timeout=30)
            changes_resp.raise_for_status()
            change_entries = changes_resp.json().get("changeEntries", [])
            for entry in change_entries:
                item = entry.get("item", {})
                path = item.get("path", "")
                if path:
                    iteration_changed_files.add(normalize_file_path(path))
    except Exception as exc:
        print(f"Warning: Could not fetch iteration changes: {exc}", file=sys.stderr)

    # Categorise files
    result = FileChangeResult()
    for f in sorted(current_file_set):
        if f not in existing_file_set:
            result.new_files.append(f)
        elif f in iteration_changed_files:
            result.modified_files.append(f)
        else:
            result.unchanged_files.append(f)

    for f in sorted(existing_file_set):
        if f not in current_file_set:
            result.deleted_files.append(f)

    # Secondary validation via git diff
    _validate_with_git_diff(result, old_commit_hash, new_commit_hash, iteration_changed_files, current_file_set)

    return result


def _validate_with_git_diff(
    result: FileChangeResult,
    old_commit_hash: str,
    new_commit_hash: str,
    iteration_changed_files: set,
    current_file_set: set,
) -> None:
    """Cross-validate file changes with local git diff.

    Adds warnings to ``result.validation_warnings`` on discrepancies.
    Always proceeds with the iterations API result as the source of truth.

    Args:
        result: FileChangeResult to add warnings to.
        old_commit_hash: Previous commit hash.
        new_commit_hash: New commit hash.
        iteration_changed_files: Files changed according to iterations API.
        current_file_set: Current file paths in the PR.
    """
    from ..subprocess_utils import run_safe

    try:
        proc = run_safe(
            ["git", "diff", f"{old_commit_hash}..{new_commit_hash}", "--name-only"],
            capture_output=True,
            text=True,
            shell=False,
        )
        if proc.returncode != 0:
            result.validation_warnings.append("git diff unavailable")
            return

        git_changed = {normalize_file_path(line) for line in proc.stdout.strip().splitlines() if line.strip()}

        # Compare: files in git diff but not in iteration changes
        for f in sorted(git_changed & current_file_set):
            if f not in iteration_changed_files:
                msg = f"File {f} changed in git diff but not in iterations API"
                result.validation_warnings.append(msg)
                print(f"Warning: {msg}", file=sys.stderr)

        # Compare: files in iteration changes but not in git diff
        for f in sorted(iteration_changed_files & current_file_set):
            if f not in git_changed:
                msg = f"File {f} changed in iterations API but not in git diff"
                result.validation_warnings.append(msg)
                print(f"Warning: {msg}", file=sys.stderr)
    except Exception:
        result.validation_warnings.append("git diff unavailable")


def _print_dry_run_plan(
    pull_request_id: int,
    files: list[str],
    folders: dict[str, list[str]],
) -> None:
    """Print the scaffolding plan without making API calls.

    Folder-level threads have been eliminated; file threads, the overall
    PR summary thread, and a Review Activity Log thread are created
    (N + 3 thread-creation POST calls in total; additional non-POST calls
    may be made when initializing the activity log).

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
        print(f"  [DRY RUN] Would group files under folder: {folder_name}")
    print("  [DRY RUN] Would create overall PR summary thread")
    print("  [DRY RUN] Would create Review Activity Log thread")
    api_calls = len(files) + 3
    print(f"  [DRY RUN] Total API calls: {api_calls}")


def scaffold_review_threads(
    pull_request_id: int,
    files: list[str],
    config: AzureDevOpsConfig,
    repo_id: str,
    repo_name: str,
    latest_iteration_id: int,
    requests_module: Any,
    headers: dict[str, str],
    dry_run: bool = False,
    commit_hash: str | None = None,
    model_id: str | None = None,
    rebase_conflicts: bool = False,
) -> ReviewState | None:
    """Create all summary threads upfront before reviewing files.

    For a PR with N files, creates:
      - N file summary threads (anchored to file path, no line)
      - 1 overall PR summary thread (PR-level)
      - 1 Review Activity Log thread (PR-level)

    Folder-level threads have been eliminated; folders are now lightweight
    groupings (``FolderGroup``) within the overall PR summary comment.

    Commit-hash-based idempotency:
      - Same commit, same model, review complete → skip, post activity log.
      - Same commit, same model, in progress (< 2h) → abort, post warning.
      - Same commit, same model, stale session (≥ 2h) → resume.
      - Same commit, different model → skip scaffolding, post activity log.
      - Different commit → incremental re-scaffolding.

    An incomplete state file (overallSummary.threadId == 0) triggers a full
    re-scaffold from scratch.

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
        commit_hash: Commit hash (``lastMergeSourceCommit.commitId``) from
            the Azure DevOps PR API.
        model_id: AI model identifier that initiated scaffolding.
        rebase_conflicts: True if rebase conflicts were detected during checkout.

    Returns:
        ReviewState with all thread IDs saved.  Returns the existing state
        when scaffolding is skipped (already reviewed / different model).
        Returns None when ``dry_run=True`` or when a recent review session
        by the same model is already in progress (aborted to avoid
        duplicate reviews).
    """
    effective_model = model_id or "unknown"
    now = datetime.now(timezone.utc)

    # -------------------------------------------------------------------
    # Idempotency check: load existing state and decide on action
    # -------------------------------------------------------------------
    existing_state: ReviewState | None = None
    try:
        existing_state = load_review_state(pull_request_id)
    except FileNotFoundError:
        pass

    if existing_state is not None and existing_state.overallSummary.threadId != 0:
        # Complete state exists — use commit-hash-based idempotency
        status = _check_session_status(existing_state, commit_hash, effective_model, now=now)
        threads_url = config.build_api_url(repo_id, "pullRequests", pull_request_id, "threads")
        short_hash = (commit_hash or "unknown")[:7]

        # Update rebase-conflict status to reflect the current checkout,
        # regardless of which idempotency path is taken below.  Paths that
        # already call save_review_state() (resume_stale, different_model)
        # will include the updated value automatically; paths that skip
        # saving (already_reviewed, first_review) get an explicit save when
        # the value has changed.
        rebase_conflicts_changed = existing_state.rebaseConflicts != rebase_conflicts
        existing_state.rebaseConflicts = rebase_conflicts

        if status == "already_reviewed":
            print(f"Commit {short_hash} already reviewed by {effective_model} for PR {pull_request_id}. Skipping.")
            if not dry_run and existing_state.activityLogThreadId:
                seq = len(existing_state.sessions) + 1
                entry = _format_activity_log_entry(
                    "✅",
                    "Already Reviewed",
                    now.isoformat(),
                    effective_model,
                    short_hash,
                    "n/a",
                    "Commit already reviewed by this model. No action taken.",
                    seq,
                )
                try:
                    _post_activity_log_entry(
                        requests_module,
                        headers,
                        threads_url,
                        existing_state.activityLogThreadId,
                        entry,
                    )
                except Exception as exc:
                    print(f"Warning: Could not post activity log entry: {exc}", file=sys.stderr)
            if rebase_conflicts_changed and not dry_run:
                save_review_state(existing_state)
            return existing_state

        if status == "in_progress":
            # Find the active session for the warning message
            active_session = None
            for s in existing_state.sessions:
                if (
                    s.modelId == effective_model
                    and s.status == "in_progress"
                    and (s.commitHash or "") == (commit_hash or "")
                ):
                    active_session = s
                    break
            active_id = active_session.sessionId if active_session else "unknown"
            active_start = active_session.startedUtc if active_session else "unknown"
            print(
                f"Review already in progress for commit {short_hash} by {effective_model} "
                f"(session {active_id}). Aborting.",
            )
            if not dry_run and existing_state.activityLogThreadId:
                seq = len(existing_state.sessions) + 1
                detail = (
                    f"A review session is currently in progress "
                    f"(session `{active_id}` started at {active_start}). Aborting."
                )
                entry = _format_activity_log_entry(
                    "⚠️",
                    "In Progress",
                    now.isoformat(),
                    effective_model,
                    short_hash,
                    "n/a",
                    detail,
                    seq,
                )
                try:
                    _post_activity_log_entry(
                        requests_module,
                        headers,
                        threads_url,
                        existing_state.activityLogThreadId,
                        entry,
                    )
                except Exception as exc:
                    print(f"Warning: Could not post activity log entry: {exc}", file=sys.stderr)
            if rebase_conflicts_changed and not dry_run:
                save_review_state(existing_state)
            return None

        if status == "resume_stale":
            reviewed = sum(1 for fe in existing_state.files.values() if fe.status != ReviewStatus.UNREVIEWED.value)
            total = len(existing_state.files)
            print(f"Resuming stale review session for PR {pull_request_id} ({reviewed}/{total} files reviewed).")
            if dry_run:
                return existing_state

            transitioned_sessions = _mark_stale_sessions_failed(
                existing_state,
                commit_hash or "",
                effective_model,
                now=now,
            )
            # Update activity log comments for sessions just marked failed
            if existing_state.activityLogThreadId:
                for s in transitioned_sessions:
                    if s.activityLogCommentId is not None:
                        try:
                            seq_idx = existing_state.sessions.index(s) + 1
                            _update_activity_log_comment_status(
                                requests_module,
                                headers,
                                threads_url,
                                existing_state.activityLogThreadId,
                                s.activityLogCommentId,
                                "❌",
                                "Failed",
                                s,
                                commit_hash,
                                seq_idx,
                                "Session timed out (stale).",
                            )
                        except Exception as exc:
                            print(f"Warning: Could not update activity log for failed session: {exc}", file=sys.stderr)
            stale_id = "unknown"
            if transitioned_sessions:
                stale_id = transitioned_sessions[-1].sessionId
            else:
                for s in reversed(existing_state.sessions):
                    if (
                        s.modelId == effective_model
                        and s.status == "failed"
                        and (s.commitHash or "") == (commit_hash or "")
                    ):
                        stale_id = s.sessionId
                        break
            new_session = _create_session(effective_model, commit_hash=commit_hash, now=now)
            existing_state.sessions.append(new_session)
            save_review_state(existing_state)
            if existing_state.activityLogThreadId:
                seq = len(existing_state.sessions)
                detail = f"Resuming incomplete review session `{stale_id}` ({reviewed}/{total} files reviewed)."
                entry = _format_activity_log_entry(
                    "🔄",
                    "Resuming",
                    now.isoformat(),
                    effective_model,
                    short_hash,
                    new_session.sessionId,
                    detail,
                    seq,
                )
                try:
                    reply_id = _post_activity_log_entry(
                        requests_module,
                        headers,
                        threads_url,
                        existing_state.activityLogThreadId,
                        entry,
                    )
                    new_session.activityLogCommentId = reply_id
                    save_review_state(existing_state)
                except Exception as exc:
                    print(f"Warning: Could not post activity log entry: {exc}", file=sys.stderr)
            return existing_state

        if status == "different_model":
            print(f"Additional reviewer ({effective_model}) joining review for PR {pull_request_id}.")
            if dry_run:
                return existing_state
            new_session = _create_session(effective_model, commit_hash=commit_hash, now=now)
            existing_state.sessions.append(new_session)
            save_review_state(existing_state)
            if existing_state.activityLogThreadId:
                seq = len(existing_state.sessions)
                entry = _format_activity_log_entry(
                    "🤝",
                    "Additional Reviewer",
                    now.isoformat(),
                    effective_model,
                    short_hash,
                    new_session.sessionId,
                    "Additional reviewer joining existing review for this commit.",
                    seq,
                )
                try:
                    reply_id = _post_activity_log_entry(
                        requests_module,
                        headers,
                        threads_url,
                        existing_state.activityLogThreadId,
                        entry,
                    )
                    new_session.activityLogCommentId = reply_id
                    save_review_state(existing_state)
                except Exception as exc:
                    print(f"Warning: Could not post activity log entry: {exc}", file=sys.stderr)
            return existing_state

        if status == "different_commit":
            # Incremental re-scaffolding
            return _incremental_rescaffold(
                existing_state=existing_state,
                pull_request_id=pull_request_id,
                files=files,
                config=config,
                repo_id=repo_id,
                repo_name=repo_name,
                latest_iteration_id=latest_iteration_id,
                requests_module=requests_module,
                headers=headers,
                dry_run=dry_run,
                commit_hash=commit_hash,
                model_id=effective_model,
                now=now,
                rebase_conflicts=rebase_conflicts,
            )

        # status == "first_review" — same commit, no sessions recorded.
        # If the state is already complete (all threads exist), skip scaffolding.
        # This is the backward-compat path for states created before session
        # tracking was introduced.
        if status == "first_review":
            print(f"Scaffolding already exists for PR {pull_request_id}. Skipping.")
            if rebase_conflicts_changed and not dry_run:
                save_review_state(existing_state)
            return existing_state

    elif existing_state is not None and existing_state.overallSummary.threadId == 0:
        print(f"Incomplete scaffolding detected for PR {pull_request_id}. Re-scaffolding from scratch.")

    # -------------------------------------------------------------------
    # First-time scaffolding (or incomplete state re-scaffold)
    # -------------------------------------------------------------------
    # Before creating new threads, check if the PR already has agdt-marker
    # threads (e.g., from a prior review session whose state.json was lost).
    # If found, recover state from them to avoid creating duplicate threads.
    if not dry_run:
        recovered = _try_recover_state_from_pr_threads(
            pull_request_id=pull_request_id,
            files=files,
            config=config,
            repo_id=repo_id,
            repo_name=repo_name,
            latest_iteration_id=latest_iteration_id,
            requests_module=requests_module,
            headers=headers,
            commit_hash=commit_hash,
            model_id=effective_model,
            now=now,
            rebase_conflicts=rebase_conflicts,
        )
        if recovered is not None:
            return recovered

    return _fresh_scaffold(
        pull_request_id=pull_request_id,
        files=files,
        config=config,
        repo_id=repo_id,
        repo_name=repo_name,
        latest_iteration_id=latest_iteration_id,
        requests_module=requests_module,
        headers=headers,
        dry_run=dry_run,
        commit_hash=commit_hash,
        model_id=effective_model,
        now=now,
        rebase_conflicts=rebase_conflicts,
    )


# ---------------------------------------------------------------------------
# Internal: recover state from existing PR threads (duplicate prevention)
# ---------------------------------------------------------------------------


def _try_recover_state_from_pr_threads(
    pull_request_id: int,
    files: list[str],
    config: AzureDevOpsConfig,
    repo_id: str,
    repo_name: str,
    latest_iteration_id: int,
    requests_module: Any,
    headers: dict[str, str],
    commit_hash: str | None,
    model_id: str,
    now: datetime | None = None,
    rebase_conflicts: bool = False,
) -> ReviewState | None:
    """Attempt to recover review state from existing agdt-marker threads on the PR.

    When ``review-state.json`` is missing (e.g., different worktree scope or
    state directory was cleaned), this function fetches all threads from the PR,
    filters for agdt-review markers, and reconstructs a ReviewState from them.
    This prevents creating duplicate scaffold threads.

    Args:
        (same as scaffold_review_threads)

    Returns:
        Recovered ReviewState if agdt threads were found on the PR, else None.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    from .marker import filter_agdt_threads, parse_marker

    threads_url = config.build_api_url(repo_id, "pullRequests", pull_request_id, "threads")

    try:
        response = requests_module.get(threads_url, headers=headers, timeout=30)
        response.raise_for_status()
        all_threads = response.json().get("value", [])
    except Exception as exc:
        print(f"Warning: Could not fetch PR threads for recovery check: {exc}", file=sys.stderr)
        return None

    agdt_threads = filter_agdt_threads(all_threads)
    if not agdt_threads:
        return None

    # Classify agdt threads by marker type
    file_threads: dict[str, tuple[int, int, dict]] = {}  # file_path → (thread_id, comment_id, author)
    overall_thread_id = 0
    overall_comment_id = 0
    activity_log_thread_id = 0

    for thread in agdt_threads:
        comments = thread.get("comments", [])
        if not comments:
            continue
        first_comment = comments[0]
        content = first_comment.get("content", "")
        parsed = parse_marker(content)
        if not parsed:
            continue

        thread_id = thread.get("id", 0)
        comment_id = first_comment.get("id", 0)
        author = first_comment.get("author", {})
        marker_type = parsed.get("type", "")

        if marker_type == "file-summary":
            file_path = parsed.get("file", "")
            if file_path:
                normalized = normalize_file_path(file_path)
                file_threads[normalized] = (thread_id, comment_id, author)
        elif marker_type == "overall-summary":
            overall_thread_id = thread_id
            overall_comment_id = comment_id
        elif marker_type == "activity-log":
            activity_log_thread_id = thread_id

    # If no agdt threads of any relevant type were found, cannot recover.
    if not overall_thread_id and not file_threads and not activity_log_thread_id:
        return None

    print(
        f"Found {len(file_threads)} existing file thread(s), "
        f"{'overall summary' if overall_thread_id else 'no overall summary'}, "
        f"and {'activity log' if activity_log_thread_id else 'no activity log'} "
        f"from existing PR threads (any identity). Reusing where possible."
    )

    # Create any missing top-level threads (overall-summary, activity-log)
    # to avoid duplicates when another identity already created some threads.
    base_url = _build_pr_base_url(config, pull_request_id)

    if not overall_thread_id:
        # Create overall summary thread since none exists from any identity
        temp_state = ReviewState(
            prId=pull_request_id,
            repoId=repo_id,
            repoName=repo_name,
            project=config.project,
            organization=config.organization,
            latestIterationId=latest_iteration_id,
            scaffoldedUtc=now.isoformat(),
            overallSummary=OverallSummary(threadId=0, commentId=0),
            folders={},
            files={},
            commitHash=commit_hash,
            modelId=model_id,
            activityLogThreadId=0,
            sessions=[],
            rebaseConflicts=rebase_conflicts,
        )
        commit_url_pr = (
            build_commit_pr_url(config.organization, config.project, repo_name, pull_request_id, latest_iteration_id)
            if commit_hash and latest_iteration_id
            else None
        )
        overall_content = render_overall_summary(
            temp_state, base_url, model_name=model_id, commit_hash=commit_hash, commit_url=commit_url_pr
        )
        print("Creating overall PR summary thread (not found from any identity)...")
        overall_thread_id, overall_comment_id = _post_thread(
            requests_module,
            headers,
            threads_url,
            overall_content,
            marker=build_marker("overall-summary", pr=pull_request_id),
        )

    if not activity_log_thread_id:
        # Create activity log thread since none exists from any identity
        activity_log_content = "## Review Activity Log\n\n*This thread tracks all review sessions for this PR.*\n"
        print("Creating Review Activity Log thread (not found from any identity)...")
        activity_log_thread_id, _ = _post_thread(
            requests_module,
            headers,
            threads_url,
            activity_log_content,
            marker=build_marker("activity-log", pr=pull_request_id),
        )

    # Detect cross-identity ownership
    from .finalization.identity import IdentityCache, is_cross_identity

    identity_cache = IdentityCache()
    cached_identity = identity_cache.get_or_fetch(config.organization, headers)

    # Build recovered file entries, creating threads only for files that are missing
    file_entries: dict[str, FileEntry] = {}
    for file_path in files:
        normalized = normalize_file_path(file_path)
        folder = _get_folder_for_path(file_path)
        file_name = _get_file_name(file_path)

        thread_id, comment_id, author = file_threads.get(normalized, (0, 0, {}))
        cross_identity_flag = False

        if thread_id == 0 or comment_id == 0:
            # Create file summary thread for this file (not found from any identity)
            temp_entry = FileEntry(
                threadId=0,
                commentId=0,
                folder=folder,
                fileName=file_name,
                status=ReviewStatus.UNREVIEWED.value,
            )
            if model_id:
                initialize_model_verdicts(temp_entry, [model_id])
            commit_url_file = (
                build_commit_file_url(
                    config.organization, config.project, repo_name, pull_request_id, normalized, latest_iteration_id
                )
                if commit_hash and latest_iteration_id
                else None
            )
            content = render_file_summary(
                temp_entry, [], base_url, model_name=model_id, commit_hash=commit_hash, commit_url=commit_url_file
            )
            print(f"Creating file summary thread for {normalized} (not found from any identity)...")
            thread_id, comment_id = _post_thread(
                requests_module,
                headers,
                threads_url,
                content,
                file_path=normalized,
                marker=build_marker("file-summary", file=normalized, pr=pull_request_id),
            )
        else:
            # Thread exists from another identity — check ownership
            if cached_identity and author:
                cross_identity_flag = is_cross_identity(author, cached_identity)

        file_entry = FileEntry(
            threadId=thread_id,
            commentId=comment_id,
            folder=folder,
            fileName=file_name,
            status=ReviewStatus.UNREVIEWED.value,
            crossIdentity=cross_identity_flag,
        )
        if model_id:
            initialize_model_verdicts(file_entry, [model_id])
        file_entries[normalized] = file_entry

    # Build folder groups
    folders: dict[str, list[str]] = {}
    for file_path in files:
        folder = _get_folder_for_path(file_path)
        normalized = normalize_file_path(file_path)
        folders.setdefault(folder, []).append(normalized)
    folder_groups = {k: FolderGroup(files=v) for k, v in folders.items()}

    # Create session
    session = _create_session(model_id, commit_hash=commit_hash, now=now)

    # Build recovered state
    recovered_state = ReviewState(
        prId=pull_request_id,
        repoId=repo_id,
        repoName=repo_name,
        project=config.project,
        organization=config.organization,
        latestIterationId=latest_iteration_id,
        scaffoldedUtc=now.isoformat(),
        overallSummary=OverallSummary(threadId=overall_thread_id, commentId=overall_comment_id),
        folders=folder_groups,
        files=file_entries,
        commitHash=commit_hash,
        modelId=model_id,
        activityLogThreadId=activity_log_thread_id,
        sessions=[session],
        rebaseConflicts=rebase_conflicts,
    )
    save_review_state(recovered_state)

    _resolve_scaffold_threads(
        requests_module=requests_module,
        headers=headers,
        config=config,
        repo_id=repo_id,
        pull_request_id=pull_request_id,
        file_entries=file_entries,
        overall_thread_id=overall_thread_id,
        activity_log_thread_id=activity_log_thread_id,
    )

    # Post activity log entry noting recovery
    if activity_log_thread_id:
        short_hash = (commit_hash or "unknown")[:7]
        seq = 1
        entry = _format_activity_log_entry(
            "🔄",
            "State Recovered",
            now.isoformat(),
            model_id,
            short_hash,
            session.sessionId,
            "Review state recovered from existing PR threads (state.json was missing).",
            seq,
        )
        try:
            reply_id = _post_activity_log_entry(requests_module, headers, threads_url, activity_log_thread_id, entry)
            session.activityLogCommentId = reply_id
            save_review_state(recovered_state)
        except Exception as exc:
            print(f"Warning: Could not post recovery activity log entry: {exc}", file=sys.stderr)

    return recovered_state


# ---------------------------------------------------------------------------
# Internal: first-time full scaffolding
# ---------------------------------------------------------------------------


def _fresh_scaffold(
    pull_request_id: int,
    files: list[str],
    config: AzureDevOpsConfig,
    repo_id: str,
    repo_name: str,
    latest_iteration_id: int,
    requests_module: Any,
    headers: dict[str, str],
    dry_run: bool,
    commit_hash: str | None,
    model_id: str,
    now: datetime | None = None,
    rebase_conflicts: bool = False,
) -> ReviewState | None:
    """Perform a first-time full scaffolding of all review threads.

    Creates file threads, overall summary, activity log thread, and
    the initial session record.

    Args:
        (same as scaffold_review_threads)

    Returns:
        ReviewState, or None in dry-run mode.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Group files by top-level folder
    folders: dict[str, list[str]] = {}
    for file_path in files:
        folder = _get_folder_for_path(file_path)
        normalized = normalize_file_path(file_path)
        folders.setdefault(folder, []).append(normalized)

    if dry_run:
        _print_dry_run_plan(pull_request_id, files, folders)
        return None

    threads_url = config.build_api_url(repo_id, "pullRequests", pull_request_id, "threads")
    base_url = _build_pr_base_url(config, pull_request_id)
    scaffolded_utc = now.isoformat()

    # Create initial session
    session = _create_session(model_id, commit_hash=commit_hash, now=now)

    def _build_state(
        file_entries: dict[str, FileEntry],
        folder_groups: dict[str, FolderGroup],
        overall_thread_id: int = 0,
        overall_comment_id: int = 0,
        activity_log_thread_id: int = 0,
    ) -> ReviewState:
        return ReviewState(
            prId=pull_request_id,
            repoId=repo_id,
            repoName=repo_name,
            project=config.project,
            organization=config.organization,
            latestIterationId=latest_iteration_id,
            scaffoldedUtc=scaffolded_utc,
            overallSummary=OverallSummary(threadId=overall_thread_id, commentId=overall_comment_id),
            folders=folder_groups,
            files=file_entries,
            commitHash=commit_hash,
            modelId=model_id,
            activityLogThreadId=activity_log_thread_id,
            sessions=[session],
            rebaseConflicts=rebase_conflicts,
        )

    # Step 1: Create file summary threads
    file_entries: dict[str, FileEntry] = {}
    commit_url_pr = (
        build_commit_pr_url(config.organization, config.project, repo_name, pull_request_id, latest_iteration_id)
        if commit_hash and latest_iteration_id
        else None
    )
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
        if model_id:
            initialize_model_verdicts(temp_entry, [model_id])
        commit_url_file = (
            build_commit_file_url(
                config.organization, config.project, repo_name, pull_request_id, normalized, latest_iteration_id
            )
            if commit_hash and latest_iteration_id
            else None
        )
        content = render_file_summary(
            temp_entry, [], base_url, model_name=model_id, commit_hash=commit_hash, commit_url=commit_url_file
        )

        print(f"Creating file summary thread for {normalized}...")
        thread_id, comment_id = _post_thread(
            requests_module,
            headers,
            threads_url,
            content,
            file_path=normalized,
            marker=build_marker("file-summary", file=normalized, pr=pull_request_id),
        )
        file_entry = FileEntry(
            threadId=thread_id,
            commentId=comment_id,
            folder=folder,
            fileName=file_name,
            status=ReviewStatus.UNREVIEWED.value,
        )
        if model_id:
            initialize_model_verdicts(file_entry, [model_id])
        file_entries[normalized] = file_entry

    # Step 2: Build lightweight folder groups
    folder_groups: dict[str, FolderGroup] = {}
    for folder_name, folder_files in folders.items():
        folder_groups[folder_name] = FolderGroup(files=folder_files)

    # Persist after file threads so partial progress is not lost on failure
    save_review_state(_build_state(file_entries, folder_groups))

    # Step 3: Create overall PR summary thread
    temp_state = _build_state(file_entries, folder_groups)
    overall_content = render_overall_summary(
        temp_state, base_url, model_name=model_id, commit_hash=commit_hash, commit_url=commit_url_pr
    )
    print("Creating overall PR summary thread...")
    overall_thread_id, overall_comment_id = _post_thread(
        requests_module,
        headers,
        threads_url,
        overall_content,
        marker=build_marker("overall-summary", pr=pull_request_id),
    )

    # Step 4: Create activity log thread
    activity_log_content = "## Review Activity Log\n\n*This thread tracks all review sessions for this PR.*\n"
    print("Creating Review Activity Log thread...")
    activity_log_thread_id, _ = _post_thread(
        requests_module,
        headers,
        threads_url,
        activity_log_content,
        marker=build_marker("activity-log", pr=pull_request_id),
    )

    # Build final state and persist
    review_state = _build_state(
        file_entries,
        folder_groups,
        overall_thread_id,
        overall_comment_id,
        activity_log_thread_id,
    )
    save_review_state(review_state)

    # Post initial activity log entry
    short_hash = (commit_hash or "unknown")[:7]
    entry = _format_activity_log_entry(
        "🆕",
        "New Review",
        now.isoformat(),
        model_id,
        short_hash,
        session.sessionId,
        "Initial scaffolding and review started.",
        1,
    )
    try:
        reply_comment_id = _post_activity_log_entry(
            requests_module,
            headers,
            threads_url,
            activity_log_thread_id,
            entry,
        )
        session.activityLogCommentId = reply_comment_id
        save_review_state(review_state)
    except Exception as exc:
        print(f"Warning: Could not post initial activity log entry: {exc}", file=sys.stderr)

    # Resolve all scaffold threads so they don't block PR merging.
    # File summary threads, overall summary thread, and activity log thread are
    # all informational — they get updated via PATCH as the review progresses.
    # Leaving them "active" would show them as open items in the PR UI and
    # potentially block merge when "All comments must be resolved" is enabled.
    _resolve_scaffold_threads(
        requests_module=requests_module,
        headers=headers,
        config=config,
        repo_id=repo_id,
        pull_request_id=pull_request_id,
        file_entries=file_entries,
        overall_thread_id=overall_thread_id,
        activity_log_thread_id=activity_log_thread_id,
    )

    print(f"Scaffolding complete. Review state saved for PR {pull_request_id}.")
    return review_state


# ---------------------------------------------------------------------------
# Internal: resolve all scaffold threads to "closed" status
# ---------------------------------------------------------------------------


def _resolve_scaffold_threads(
    requests_module: Any,
    headers: dict[str, str],
    config: AzureDevOpsConfig,
    repo_id: str,
    pull_request_id: int,
    file_entries: dict[str, FileEntry],
    overall_thread_id: int,
    activity_log_thread_id: int,
) -> None:
    """Resolve all scaffold threads so they don't block PR merging.

    All scaffold threads (file summary, overall summary, activity log) are
    informational and should be in "closed" status.  They get updated via
    PATCH as the review progresses but should never block merge.

    Args:
        requests_module: requests module for HTTP calls.
        headers: Auth headers.
        config: Azure DevOps configuration.
        repo_id: Repository ID.
        pull_request_id: PR ID.
        file_entries: Dict of file path to FileEntry (for thread IDs).
        overall_thread_id: Overall summary thread ID.
        activity_log_thread_id: Activity log thread ID.
    """
    thread_ids_to_resolve = []

    # Collect file thread IDs
    for fe in file_entries.values():
        if fe.threadId:
            thread_ids_to_resolve.append(fe.threadId)

    # Overall summary thread
    if overall_thread_id:
        thread_ids_to_resolve.append(overall_thread_id)

    # Activity log thread
    if activity_log_thread_id:
        thread_ids_to_resolve.append(activity_log_thread_id)

    for thread_id in thread_ids_to_resolve:
        try:
            patch_thread_status(
                requests_module=requests_module,
                headers=headers,
                config=config,
                repo_id=repo_id,
                pull_request_id=pull_request_id,
                thread_id=thread_id,
                status="closed",
            )
        except Exception as exc:
            print(f"Warning: Could not resolve thread {thread_id}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Internal: incremental re-scaffolding on new commit
# ---------------------------------------------------------------------------


def _incremental_rescaffold(
    existing_state: ReviewState,
    pull_request_id: int,
    files: list[str],
    config: AzureDevOpsConfig,
    repo_id: str,
    repo_name: str,
    latest_iteration_id: int,
    requests_module: Any,
    headers: dict[str, str],
    dry_run: bool,
    commit_hash: str | None,
    model_id: str,
    now: datetime | None = None,
    rebase_conflicts: bool = False,
) -> ReviewState | None:
    """Perform incremental re-scaffolding for a new commit.

    Detects file changes between old and new commit, then:
      - New files: scaffold new threads.
      - Modified files: demote old comment, re-scaffold with fresh unreviewed.
      - Deleted files: demote old comment, mark as removed.
      - Unchanged files: no action.
    Updates folder groups, overall summary, and posts activity log entry.

    Args:
        (same as scaffold_review_threads + existing_state)

    Returns:
        Updated ReviewState, or None in dry-run mode.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    old_commit_hash = existing_state.commitHash or ""
    short_new_hash = (commit_hash or "unknown")[:7]

    threads_url = config.build_api_url(repo_id, "pullRequests", pull_request_id, "threads")
    base_url = _build_pr_base_url(config, pull_request_id)

    normalised_files = [normalize_file_path(f) for f in files]

    changes = detect_file_changes(
        existing_state,
        normalised_files,
        config,
        repo_id,
        pull_request_id,
        old_commit_hash,
        commit_hash or "",
        requests_module,
        headers,
    )

    n_new = len(changes.new_files)
    n_mod = len(changes.modified_files)
    n_del = len(changes.deleted_files)
    n_unch = len(changes.unchanged_files)

    print(
        f"Incremental re-scaffolding for PR {pull_request_id}: "
        f"{n_new} new, {n_mod} modified, {n_del} deleted, {n_unch} unchanged files."
    )

    commit_url_pr = (
        build_commit_pr_url(config.organization, config.project, repo_name, pull_request_id, latest_iteration_id)
        if commit_hash and latest_iteration_id
        else None
    )

    # -------------------------------------------------------------------
    # Suggestion verification gate
    # -------------------------------------------------------------------
    files_with_previous = {
        fp: fe.previousSuggestions for fp, fe in existing_state.files.items() if fe.previousSuggestions
    }
    if files_with_previous and not dry_run:
        threads_lookup = fetch_threads_lookup(requests_module, headers, threads_url)
        if threads_lookup is not None:
            changed_set = frozenset(changes.new_files + changes.modified_files + changes.deleted_files)
            verification_results = categorize_all_suggestions(files_with_previous, changed_set, threads_lookup)
            if verification_results:
                unaddressed_list, needs_review_list = partition_results(verification_results)
                if has_unaddressed(verification_results):
                    # --- Abort gate: post comments on unaddressed threads ---
                    for r in unaddressed_list:
                        try:
                            _post_reply(
                                requests_module,
                                headers,
                                threads_url,
                                r.suggestion.threadId,
                                render_unaddressed_thread_comment(short_new_hash),
                            )
                        except Exception as exc:
                            print(
                                f"Warning: Could not post unaddressed comment on thread {r.suggestion.threadId}: {exc}",
                                file=sys.stderr,
                            )

                    # Post abort summary on the overall summary thread
                    abort_summary = render_abort_summary(
                        unaddressed_list,
                        needs_review_list,
                        short_new_hash,
                    )
                    overall = existing_state.overallSummary
                    if overall.threadId:
                        try:
                            _demote_main_comment(
                                requests_module,
                                headers,
                                threads_url,
                                overall.threadId,
                                overall.commentId,
                                abort_summary,
                                commit_hash=commit_hash,
                                commit_url=commit_url_pr,
                            )
                        except Exception as exc:
                            print(f"Warning: Could not post abort summary: {exc}", file=sys.stderr)

                    # Record abort-gated session unconditionally (consistent with
                    # resume_stale and different_model paths which always create a
                    # session regardless of activityLogThreadId).
                    n_unaddr = len(unaddressed_list)
                    session = _create_session(model_id, commit_hash=commit_hash, now=now)
                    # Mark this abort-gated session as a terminal failure so it is not treated
                    # as an in-progress or resumable session by _check_session_status().
                    session.status = "failed"
                    session.completedUtc = now.isoformat()
                    existing_state.sessions.append(session)

                    # Post activity log entry (only if activity log thread exists)
                    if existing_state.activityLogThreadId:
                        seq = len(existing_state.sessions)
                        detail = f"Review blocked: {n_unaddr} unaddressed suggestion(s)."
                        entry = _format_activity_log_entry(
                            "⛔",
                            "Blocked",
                            now.isoformat(),
                            model_id,
                            short_new_hash,
                            session.sessionId,
                            detail,
                            seq,
                        )
                        try:
                            reply_id = _post_activity_log_entry(
                                requests_module,
                                headers,
                                threads_url,
                                existing_state.activityLogThreadId,
                                entry,
                            )
                            session.activityLogCommentId = reply_id
                        except Exception as exc:
                            print(f"Warning: Could not post activity log: {exc}", file=sys.stderr)

                    existing_state.commitHash = commit_hash
                    save_review_state(existing_state)
                    print(
                        f"⛔ Review blocked: {n_unaddr} unaddressed suggestion(s). Address them and push a new commit."
                    )
                    return existing_state

                # All are needs_review — set verification status on affected files
                for r in needs_review_list:
                    fe = existing_state.files.get(r.file_path)
                    if fe:
                        fe.suggestionVerificationStatus = "pending_verification"
        else:
            print("Warning: Could not fetch PR threads for verification. Proceeding.", file=sys.stderr)

    if dry_run:
        print(f"[DRY RUN] Would re-scaffold PR {pull_request_id} for commit {short_new_hash}")
        for f in changes.new_files:
            print(f"  [DRY RUN] New file: {f}")
        for f in changes.modified_files:
            print(f"  [DRY RUN] Modified file: {f}")
        for f in changes.deleted_files:
            print(f"  [DRY RUN] Deleted file: {f}")
        for f in changes.unchanged_files:
            print(f"  [DRY RUN] Unchanged file: {f}")
        return None

    # Process new files
    for file_path in changes.new_files:
        folder = _get_folder_for_path(file_path)
        file_name = _get_file_name(file_path)
        temp_entry = FileEntry(
            threadId=0,
            commentId=0,
            folder=folder,
            fileName=file_name,
            status=ReviewStatus.UNREVIEWED.value,
        )
        if model_id:
            initialize_model_verdicts(temp_entry, [model_id])
        commit_url_file = (
            build_commit_file_url(
                config.organization, config.project, repo_name, pull_request_id, file_path, latest_iteration_id
            )
            if commit_hash and latest_iteration_id
            else None
        )
        content = render_file_summary(
            temp_entry, [], base_url, model_name=model_id, commit_hash=commit_hash, commit_url=commit_url_file
        )
        print(f"Scaffolding new file thread for {file_path}...")
        thread_id, comment_id = _post_thread(
            requests_module,
            headers,
            threads_url,
            content,
            file_path=file_path,
            marker=build_marker("file-summary", file=file_path, pr=pull_request_id),
        )
        new_file_entry = FileEntry(
            threadId=thread_id,
            commentId=comment_id,
            folder=folder,
            fileName=file_name,
            status=ReviewStatus.UNREVIEWED.value,
        )
        if model_id:
            initialize_model_verdicts(new_file_entry, [model_id])
        existing_state.files[file_path] = new_file_entry

    # Process modified files
    for file_path in changes.modified_files:
        fe = existing_state.files.get(file_path)
        if fe and fe.threadId:
            commit_url_file = (
                build_commit_file_url(
                    config.organization, config.project, repo_name, pull_request_id, file_path, latest_iteration_id
                )
                if commit_hash and latest_iteration_id
                else None
            )
            try:
                _demote_main_comment(
                    requests_module,
                    headers,
                    threads_url,
                    fe.threadId,
                    fe.commentId,
                    render_file_summary(
                        replace(
                            fe,
                            status=ReviewStatus.UNREVIEWED.value,
                            summary=None,
                            suggestions=[],
                            modelVerdicts=[ModelVerdict(modelId=mv.modelId) for mv in fe.modelVerdicts],
                            consolidationStatus=None,
                        ),
                        [],
                        base_url,
                        model_name=model_id,
                        commit_hash=commit_hash,
                        commit_url=commit_url_file,
                    ),
                    commit_hash=commit_hash,
                    commit_url=commit_url_file,
                )
            except Exception as exc:
                print(f"Warning: Could not demote comment for {file_path}: {exc}", file=sys.stderr)
            # Reset file state
            fe.previousSuggestions = list(fe.suggestions) if fe.suggestions else []
            fe.suggestions = []
            fe.status = ReviewStatus.UNREVIEWED.value
            fe.summary = None
            for mv in fe.modelVerdicts:
                mv.status = ReviewStatus.UNREVIEWED.value
                mv.verdictType = None
            fe.consolidationStatus = None

    # Process deleted files
    for file_path in changes.deleted_files:
        fe = existing_state.files.get(file_path)
        if fe and fe.threadId:
            removed_msg = f"🗑️ File removed in commit `{short_new_hash}`"
            try:
                _demote_main_comment(
                    requests_module,
                    headers,
                    threads_url,
                    fe.threadId,
                    fe.commentId,
                    removed_msg,
                    commit_hash=commit_hash,
                )
            except Exception as exc:
                print(f"Warning: Could not demote comment for deleted {file_path}: {exc}", file=sys.stderr)
            fe.status = ReviewStatus.APPROVED.value
            fe.summary = "File removed"

    # Update folder groups
    all_current_files = set(changes.new_files + changes.modified_files + changes.unchanged_files)
    new_folders: dict[str, list[str]] = {}
    for f in sorted(all_current_files):
        folder = _get_folder_for_path(f)
        new_folders.setdefault(folder, []).append(f)
    # Keep existing empty folder groups for deleted files
    for folder_name in existing_state.folders:
        if folder_name not in new_folders:
            new_folders[folder_name] = []
    existing_state.folders = {k: FolderGroup(files=v) for k, v in new_folders.items()}

    # Update commit hash, iteration, and rebase conflict status.
    # rebaseConflicts must be set before rendering the overall summary so the
    # warning banner is included in the posted comment.
    existing_state.commitHash = commit_hash
    existing_state.latestIterationId = latest_iteration_id
    existing_state.rebaseConflicts = rebase_conflicts

    # Demote and update overall summary
    if n_new > 0 or n_mod > 0 or n_del > 0:
        overall = existing_state.overallSummary
        if overall.threadId:
            new_summary = render_overall_summary(
                existing_state, base_url, model_name=model_id, commit_hash=commit_hash, commit_url=commit_url_pr
            )
            try:
                _demote_main_comment(
                    requests_module,
                    headers,
                    threads_url,
                    overall.threadId,
                    overall.commentId,
                    new_summary,
                    commit_hash=commit_hash,
                    commit_url=commit_url_pr,
                )
            except Exception as exc:
                print(f"Warning: Could not update overall summary: {exc}", file=sys.stderr)
    elif n_unch > 0 and n_new == 0 and n_mod == 0 and n_del == 0:
        # Rebase with no changes — demote and re-render summary
        overall = existing_state.overallSummary
        if overall.threadId:
            new_summary = render_overall_summary(
                existing_state, base_url, model_name=model_id, commit_hash=commit_hash, commit_url=commit_url_pr
            )
            try:
                _demote_main_comment(
                    requests_module,
                    headers,
                    threads_url,
                    overall.threadId,
                    overall.commentId,
                    new_summary,
                    commit_hash=commit_hash,
                    commit_url=commit_url_pr,
                )
            except Exception as exc:
                print(f"Warning: Could not update overall summary: {exc}", file=sys.stderr)

    # Create new session
    session = _create_session(model_id, commit_hash=commit_hash, now=now)
    existing_state.sessions.append(session)

    save_review_state(existing_state)

    # Post activity log entry
    if existing_state.activityLogThreadId:
        seq = len(existing_state.sessions)
        if n_new == 0 and n_mod == 0 and n_del == 0:
            detail = "New commit detected (rebase). No file content changes. Previous review preserved."
            emoji, status_text = "🔁", "Rebase"
        else:
            detail = (
                f"New commit detected. Incremental re-scaffolding: "
                f"{n_new} new, {n_mod} modified, {n_del} deleted, {n_unch} unchanged files."
            )
            emoji, status_text = "🔀", "New Commit"
        entry = _format_activity_log_entry(
            emoji,
            status_text,
            now.isoformat(),
            model_id,
            short_new_hash,
            session.sessionId,
            detail,
            seq,
        )
        try:
            reply_id = _post_activity_log_entry(
                requests_module,
                headers,
                threads_url,
                existing_state.activityLogThreadId,
                entry,
            )
            session.activityLogCommentId = reply_id
            save_review_state(existing_state)
        except Exception as exc:
            print(f"Warning: Could not post activity log entry: {exc}", file=sys.stderr)

    print(f"Incremental re-scaffolding complete for PR {pull_request_id}.")
    return existing_state
