"""Scaffolding for PR review threads.

Creates all summary threads upfront before the agent begins reviewing files.
For a PR with N files:
  - N file summary threads (anchored to file path, no line)
  - 1 overall PR summary thread (PR-level)
  - 1 Review Activity Log thread (PR-level, no file context)
Total: N + 2 API calls (one-time upfront cost).

Folder-level threads have been eliminated; folders are now lightweight
groupings within the overall PR summary comment.

Session management, commit-hash-based idempotency, and incremental
re-scaffolding are also handled here.
"""

import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from .config import AzureDevOpsConfig
from .review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewSession,
    ReviewState,
    ReviewStatus,
    load_review_state,
    normalize_file_path,
    save_review_state,
)
from .review_templates import render_file_summary, render_overall_summary

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
    encoded_project = quote(config.project, safe="")
    encoded_repo = quote(config.repository, safe="")
    return f"{org}/{encoded_project}/_git/{encoded_repo}/pullrequest/{pull_request_id}"


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


# ---------------------------------------------------------------------------
# FileChangeResult — differential file detection result
# ---------------------------------------------------------------------------


@dataclass
class FileChangeResult:
    """Result of differential file detection between two commits.

    Categorises every file in the PR as new, modified, deleted, or unchanged
    relative to a previous scaffolding run.
    """

    new_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    deleted_files: List[str] = field(default_factory=list)
    unchanged_files: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Reply / demotion helpers
# ---------------------------------------------------------------------------


def _post_reply(
    requests_module: Any,
    headers: Dict[str, str],
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
    url = f"{threads_url}/{thread_id}/comments"
    body = {"content": content, "commentType": "text"}
    response = requests_module.post(url, headers=headers, json=body, timeout=30)
    response.raise_for_status()
    return response.json()["id"]


def _get_thread_comments(
    requests_module: Any,
    headers: Dict[str, str],
    threads_url: str,
    thread_id: int,
) -> List[Dict[str, Any]]:
    """GET a thread and return its comments list.

    Args:
        requests_module: requests module for HTTP calls.
        headers: Auth headers.
        threads_url: Base threads URL.
        thread_id: Thread to fetch.

    Returns:
        List of comment dicts from the API response.
    """
    url = f"{threads_url}/{thread_id}"
    response = requests_module.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json().get("comments", [])


def _patch_comment_content(
    requests_module: Any,
    headers: Dict[str, str],
    threads_url: str,
    thread_id: int,
    comment_id: int,
    new_content: str,
) -> None:
    """PATCH a single comment's content.

    Args:
        requests_module: requests module for HTTP calls.
        headers: Auth headers.
        threads_url: Base threads URL.
        thread_id: Thread containing the comment.
        comment_id: Comment to update.
        new_content: New markdown content.
    """
    url = f"{threads_url}/{thread_id}/comments/{comment_id}"
    response = requests_module.patch(url, headers=headers, json={"content": new_content}, timeout=30)
    response.raise_for_status()


def _demote_main_comment(
    requests_module: Any,
    headers: Dict[str, str],
    threads_url: str,
    thread_id: int,
    comment_id: int,
    new_main_content: str,
) -> int:
    """Read current main comment, post it as reply, PATCH main with new content.

    Steps:
      1. GET the thread to read current main comment content.
      2. POST current content as a reply (preserving it as history).
      3. PATCH the main comment with ``new_main_content``.

    Args:
        requests_module: requests module for HTTP calls.
        headers: Auth headers.
        threads_url: Base threads URL.
        thread_id: Thread whose main comment is being demoted.
        comment_id: The main comment ID (usually 1).
        new_main_content: New content for the main comment.

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

    # Step 2: Post old content as a reply
    reply_id = _post_reply(requests_module, headers, threads_url, thread_id, old_content)

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
    headers: Dict[str, str],
    threads_url: str,
    thread_id: int,
    comment_id: int,
    entry_content: str,
) -> None:
    """Post a new activity log entry to the activity log thread.

    The main comment always shows the latest entry; older entries are pushed
    down as replies.  Implementation: read main comment, POST it as reply,
    PATCH main with the new entry.

    Args:
        requests_module: requests module for HTTP calls.
        headers: Auth headers.
        threads_url: Base threads URL.
        thread_id: Activity log thread ID.
        comment_id: Activity log main comment ID.
        entry_content: Formatted markdown for the new entry.
    """
    _demote_main_comment(requests_module, headers, threads_url, thread_id, comment_id, entry_content)


# ---------------------------------------------------------------------------
# Session management helpers
# ---------------------------------------------------------------------------


def _check_session_status(
    existing_state: ReviewState,
    commit_hash: Optional[str],
    model_id: str,
    now: Optional[datetime] = None,
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
        matching_sessions = [
            s for s in existing_state.sessions if s.modelId == model_id
        ]
        for session in matching_sessions:
            if session.status == "completed":
                return "already_reviewed"
            if session.status == "in_progress":
                started = datetime.fromisoformat(session.startedUtc)
                if now - started < STALE_SESSION_THRESHOLD:
                    return "in_progress"
                return "resume_stale"
        # No matching sessions for this model — check if different model has sessions
        if existing_state.sessions:
            return "different_model"
        return "first_review"

    # Different commit hash — handled by caller (incremental re-scaffolding)
    return "different_commit"


def _mark_stale_sessions_failed(
    existing_state: ReviewState,
    commit_hash: str,
    model_id: str,
    now: Optional[datetime] = None,
) -> None:
    """Mark all stale in-progress sessions as failed for a commit + model.

    Args:
        existing_state: Review state (mutated in-place).
        commit_hash: Current commit hash.
        model_id: Current model identifier.
        now: Current time (injectable for testing).
    """
    if now is None:
        now = datetime.now(timezone.utc)
    for session in existing_state.sessions:
        if (
            session.modelId == model_id
            and session.status == "in_progress"
            and existing_state.commitHash == commit_hash
        ):
            started = datetime.fromisoformat(session.startedUtc)
            if now - started >= STALE_SESSION_THRESHOLD:
                session.status = "failed"
                session.completedUtc = now.isoformat()


def _create_session(
    model_id: str,
    now: Optional[datetime] = None,
) -> ReviewSession:
    """Create a new ReviewSession with in_progress status.

    Args:
        model_id: AI model identifier.
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
    )


# ---------------------------------------------------------------------------
# Differential file detection
# ---------------------------------------------------------------------------


def detect_file_changes(
    existing_state: ReviewState,
    current_files: List[str],
    config: AzureDevOpsConfig,
    repo_id: str,
    pull_request_id: int,
    old_commit_hash: str,
    new_commit_hash: str,
    requests_module: Any,
    headers: Dict[str, str],
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
    files: List[str],
    folders: Dict[str, List[str]],
) -> None:
    """Print the scaffolding plan without making API calls.

    Folder-level threads have been eliminated; only file threads and
    the overall PR summary thread are created (N + 1 API calls).

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
    api_calls = len(files) + 1
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
    commit_hash: Optional[str] = None,
    model_id: Optional[str] = None,
) -> Optional[ReviewState]:
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

    Returns:
        ReviewState with all thread IDs saved.  Returns the existing state
        when scaffolding is skipped (already reviewed / in progress / different
        model).  Returns None when ``dry_run=True`` or when the review is
        aborted (in-progress session by another agent).
    """
    effective_model = model_id or "unknown"
    now = datetime.now(timezone.utc)

    # -------------------------------------------------------------------
    # Idempotency check: load existing state and decide on action
    # -------------------------------------------------------------------
    existing_state: Optional[ReviewState] = None
    try:
        existing_state = load_review_state(pull_request_id)
    except FileNotFoundError:
        pass

    if existing_state is not None and existing_state.overallSummary.threadId != 0:
        # Complete state exists — use commit-hash-based idempotency
        status = _check_session_status(existing_state, commit_hash, effective_model, now=now)
        threads_url = config.build_api_url(repo_id, "pullRequests", pull_request_id, "threads")
        base_url = _build_pr_base_url(config, pull_request_id)
        short_hash = (commit_hash or "unknown")[:7]

        if status == "already_reviewed":
            print(f"Commit {short_hash} already reviewed by {effective_model} for PR {pull_request_id}. Skipping.")
            if not dry_run and existing_state.activityLogThreadId:
                seq = len(existing_state.sessions) + 1
                entry = _format_activity_log_entry(
                    "✅", "Already Reviewed", now.isoformat(), effective_model, short_hash,
                    "n/a", "Commit already reviewed by this model. No action taken.", seq,
                )
                try:
                    _post_activity_log_entry(
                        requests_module, headers, threads_url,
                        existing_state.activityLogThreadId, 1, entry,
                    )
                except Exception as exc:
                    print(f"Warning: Could not post activity log entry: {exc}", file=sys.stderr)
            return existing_state

        if status == "in_progress":
            # Find the active session for the warning message
            active_session = None
            for s in existing_state.sessions:
                if s.modelId == effective_model and s.status == "in_progress":
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
                    "⚠️", "In Progress", now.isoformat(), effective_model, short_hash,
                    "n/a", detail, seq,
                )
                try:
                    _post_activity_log_entry(
                        requests_module, headers, threads_url,
                        existing_state.activityLogThreadId, 1, entry,
                    )
                except Exception as exc:
                    print(f"Warning: Could not post activity log entry: {exc}", file=sys.stderr)
            return None

        if status == "resume_stale":
            _mark_stale_sessions_failed(existing_state, commit_hash or "", effective_model, now=now)
            reviewed = sum(1 for fe in existing_state.files.values() if fe.status != ReviewStatus.UNREVIEWED.value)
            total = len(existing_state.files)
            stale_id = "unknown"
            for s in existing_state.sessions:
                if s.modelId == effective_model and s.status == "failed":
                    stale_id = s.sessionId
                    break
            print(f"Resuming stale review session for PR {pull_request_id} ({reviewed}/{total} files reviewed).")
            new_session = _create_session(effective_model, now=now)
            existing_state.sessions.append(new_session)
            if not dry_run:
                save_review_state(existing_state)
                if existing_state.activityLogThreadId:
                    seq = len(existing_state.sessions)
                    detail = (
                        f"Resuming incomplete review session `{stale_id}` "
                        f"({reviewed}/{total} files reviewed)."
                    )
                    entry = _format_activity_log_entry(
                        "🔄", "Resuming", now.isoformat(), effective_model, short_hash,
                        new_session.sessionId, detail, seq,
                    )
                    try:
                        _post_activity_log_entry(
                            requests_module, headers, threads_url,
                            existing_state.activityLogThreadId, 1, entry,
                        )
                    except Exception as exc:
                        print(f"Warning: Could not post activity log entry: {exc}", file=sys.stderr)
            return existing_state

        if status == "different_model":
            print(f"Additional reviewer ({effective_model}) joining review for PR {pull_request_id}.")
            new_session = _create_session(effective_model, now=now)
            existing_state.sessions.append(new_session)
            if not dry_run:
                save_review_state(existing_state)
                if existing_state.activityLogThreadId:
                    seq = len(existing_state.sessions)
                    entry = _format_activity_log_entry(
                        "🤝", "Additional Reviewer", now.isoformat(), effective_model, short_hash,
                        new_session.sessionId, "Additional reviewer joining existing review for this commit.", seq,
                    )
                    try:
                        _post_activity_log_entry(
                            requests_module, headers, threads_url,
                            existing_state.activityLogThreadId, 1, entry,
                        )
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
            )

        # status == "first_review" — same commit, no sessions recorded.
        # If the state is already complete (all threads exist), skip scaffolding.
        # This is the backward-compat path for states created before session
        # tracking was introduced.
        if status == "first_review":
            print(f"Scaffolding already exists for PR {pull_request_id}. Skipping.")
            return existing_state

    elif existing_state is not None and existing_state.overallSummary.threadId == 0:
        print(f"Incomplete scaffolding detected for PR {pull_request_id}. Re-scaffolding from scratch.")

    # -------------------------------------------------------------------
    # First-time scaffolding (or incomplete state re-scaffold)
    # -------------------------------------------------------------------
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
    )


# ---------------------------------------------------------------------------
# Internal: first-time full scaffolding
# ---------------------------------------------------------------------------


def _fresh_scaffold(
    pull_request_id: int,
    files: List[str],
    config: AzureDevOpsConfig,
    repo_id: str,
    repo_name: str,
    latest_iteration_id: int,
    requests_module: Any,
    headers: Dict[str, str],
    dry_run: bool,
    commit_hash: Optional[str],
    model_id: str,
    now: Optional[datetime] = None,
) -> Optional[ReviewState]:
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
    scaffolded_utc = now.isoformat()

    # Create initial session
    session = _create_session(model_id, now=now)

    def _build_state(
        file_entries: Dict[str, FileEntry],
        folder_groups: Dict[str, FolderGroup],
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
        )

    # Step 1: Create file summary threads
    file_entries: Dict[str, FileEntry] = {}
    for file_path in files:
        normalized = normalize_file_path(file_path)
        folder = _get_folder_for_path(file_path)
        file_name = _get_file_name(file_path)

        temp_entry = FileEntry(
            threadId=0, commentId=0, folder=folder, fileName=file_name,
            status=ReviewStatus.UNREVIEWED.value,
        )
        content = render_file_summary(temp_entry, [], base_url)

        print(f"Creating file summary thread for {normalized}...")
        thread_id, comment_id = _post_thread(requests_module, headers, threads_url, content, file_path=normalized)
        file_entries[normalized] = FileEntry(
            threadId=thread_id, commentId=comment_id, folder=folder, fileName=file_name,
            status=ReviewStatus.UNREVIEWED.value,
        )

    # Step 2: Build lightweight folder groups
    folder_groups: Dict[str, FolderGroup] = {}
    for folder_name, folder_files in folders.items():
        folder_groups[folder_name] = FolderGroup(files=folder_files)

    # Persist after file threads so partial progress is not lost on failure
    save_review_state(_build_state(file_entries, folder_groups))

    # Step 3: Create overall PR summary thread
    temp_state = _build_state(file_entries, folder_groups)
    overall_content = render_overall_summary(temp_state, base_url)
    print("Creating overall PR summary thread...")
    overall_thread_id, overall_comment_id = _post_thread(requests_module, headers, threads_url, overall_content)

    # Step 4: Create activity log thread
    activity_log_content = (
        "## Review Activity Log\n\n*This thread tracks all review sessions for this PR.*\n"
    )
    print("Creating Review Activity Log thread...")
    activity_log_thread_id, _ = _post_thread(requests_module, headers, threads_url, activity_log_content)

    # Build final state and persist
    review_state = _build_state(
        file_entries, folder_groups, overall_thread_id, overall_comment_id, activity_log_thread_id,
    )
    save_review_state(review_state)

    # Post initial activity log entry
    short_hash = (commit_hash or "unknown")[:7]
    entry = _format_activity_log_entry(
        "🆕", "New Review", now.isoformat(), model_id, short_hash,
        session.sessionId, "Initial scaffolding and review started.", 1,
    )
    try:
        _post_activity_log_entry(
            requests_module, headers, threads_url, activity_log_thread_id, 1, entry,
        )
    except Exception as exc:
        print(f"Warning: Could not post initial activity log entry: {exc}", file=sys.stderr)

    print(f"Scaffolding complete. Review state saved for PR {pull_request_id}.")
    return review_state


# ---------------------------------------------------------------------------
# Internal: incremental re-scaffolding on new commit
# ---------------------------------------------------------------------------


def _incremental_rescaffold(
    existing_state: ReviewState,
    pull_request_id: int,
    files: List[str],
    config: AzureDevOpsConfig,
    repo_id: str,
    repo_name: str,
    latest_iteration_id: int,
    requests_module: Any,
    headers: Dict[str, str],
    dry_run: bool,
    commit_hash: Optional[str],
    model_id: str,
    now: Optional[datetime] = None,
) -> Optional[ReviewState]:
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
    short_old_hash = old_commit_hash[:7] if old_commit_hash else "unknown"
    short_new_hash = (commit_hash or "unknown")[:7]

    threads_url = config.build_api_url(repo_id, "pullRequests", pull_request_id, "threads")
    base_url = _build_pr_base_url(config, pull_request_id)

    normalised_files = [normalize_file_path(f) for f in files]

    changes = detect_file_changes(
        existing_state, normalised_files, config, repo_id, pull_request_id,
        old_commit_hash, commit_hash or "", requests_module, headers,
    )

    n_new = len(changes.new_files)
    n_mod = len(changes.modified_files)
    n_del = len(changes.deleted_files)
    n_unch = len(changes.unchanged_files)

    print(
        f"Incremental re-scaffolding for PR {pull_request_id}: "
        f"{n_new} new, {n_mod} modified, {n_del} deleted, {n_unch} unchanged files."
    )

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
            threadId=0, commentId=0, folder=folder, fileName=file_name,
            status=ReviewStatus.UNREVIEWED.value,
        )
        content = render_file_summary(temp_entry, [], base_url)
        print(f"Scaffolding new file thread for {file_path}...")
        thread_id, comment_id = _post_thread(requests_module, headers, threads_url, content, file_path=file_path)
        existing_state.files[file_path] = FileEntry(
            threadId=thread_id, commentId=comment_id, folder=folder, fileName=file_name,
            status=ReviewStatus.UNREVIEWED.value,
        )

    # Process modified files
    for file_path in changes.modified_files:
        fe = existing_state.files.get(file_path)
        if fe and fe.threadId:
            historical_prefix = f"📋 Review from previous version (commit `{short_old_hash}`):\n\n"
            try:
                _demote_main_comment(
                    requests_module, headers, threads_url, fe.threadId, fe.commentId,
                    render_file_summary(
                        FileEntry(
                            threadId=fe.threadId, commentId=fe.commentId, folder=fe.folder,
                            fileName=fe.fileName, status=ReviewStatus.UNREVIEWED.value,
                        ),
                        [], base_url,
                    ),
                )
            except Exception as exc:
                print(f"Warning: Could not demote comment for {file_path}: {exc}", file=sys.stderr)
            # Reset file state
            fe.previousSuggestions = list(fe.suggestions) if fe.suggestions else []
            fe.suggestions = []
            fe.status = ReviewStatus.UNREVIEWED.value
            fe.summary = None

    # Process deleted files
    for file_path in changes.deleted_files:
        fe = existing_state.files.get(file_path)
        if fe and fe.threadId:
            removed_msg = f"🗑️ File removed in commit `{short_new_hash}`"
            try:
                _demote_main_comment(
                    requests_module, headers, threads_url, fe.threadId, fe.commentId, removed_msg,
                )
            except Exception as exc:
                print(f"Warning: Could not demote comment for deleted {file_path}: {exc}", file=sys.stderr)
            fe.status = ReviewStatus.APPROVED.value
            fe.summary = "File removed"

    # Update folder groups
    all_current_files = set(changes.new_files + changes.modified_files + changes.unchanged_files)
    new_folders: Dict[str, List[str]] = {}
    for f in sorted(all_current_files):
        folder = _get_folder_for_path(f)
        new_folders.setdefault(folder, []).append(f)
    # Keep existing empty folder groups for deleted files
    for folder_name in existing_state.folders:
        if folder_name not in new_folders:
            new_folders[folder_name] = []
    existing_state.folders = {k: FolderGroup(files=v) for k, v in new_folders.items()}

    # Demote and update overall summary
    if n_new > 0 or n_mod > 0 or n_del > 0:
        overall = existing_state.overallSummary
        if overall.threadId:
            new_summary = render_overall_summary(existing_state, base_url)
            try:
                _demote_main_comment(
                    requests_module, headers, threads_url, overall.threadId, overall.commentId, new_summary,
                )
            except Exception as exc:
                print(f"Warning: Could not update overall summary: {exc}", file=sys.stderr)
    elif n_unch > 0 and n_new == 0 and n_mod == 0 and n_del == 0:
        # Rebase with no changes — demote and re-render summary
        overall = existing_state.overallSummary
        if overall.threadId:
            new_summary = render_overall_summary(existing_state, base_url)
            try:
                _demote_main_comment(
                    requests_module, headers, threads_url, overall.threadId, overall.commentId, new_summary,
                )
            except Exception as exc:
                print(f"Warning: Could not update overall summary: {exc}", file=sys.stderr)

    # Update commit hash and iteration
    existing_state.commitHash = commit_hash
    existing_state.latestIterationId = latest_iteration_id

    # Create new session
    session = _create_session(model_id, now=now)
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
            emoji, status_text, now.isoformat(), model_id, short_new_hash,
            session.sessionId, detail, seq,
        )
        try:
            _post_activity_log_entry(
                requests_module, headers, threads_url,
                existing_state.activityLogThreadId, 1, entry,
            )
        except Exception as exc:
            print(f"Warning: Could not post activity log entry: {exc}", file=sys.stderr)

    print(f"Incremental re-scaffolding complete for PR {pull_request_id}.")
    return existing_state
