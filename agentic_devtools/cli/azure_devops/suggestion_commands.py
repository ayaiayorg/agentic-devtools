"""CLI commands for AI reviewer suggestion evaluation.

Provides two sync commands that the AI reviewer uses after evaluating
"Needs Review" suggestions:

* ``confirm_suggestion_addressed`` — resolve the thread and post a
  confirmation reply.
* ``reject_suggestion_resolution`` — reactivate the thread and post an
  explanation reply.

Both commands read state keys and perform Azure DevOps API calls.
"""

import sys
from typing import Any, Dict

from ...state import get_pull_request_id, get_thread_id, get_value, is_dry_run
from .auth import get_auth_headers, get_pat
from .config import AzureDevOpsConfig
from .helpers import get_repository_id, require_requests, resolve_thread_by_id


def _post_thread_reply(
    requests_module: Any,
    headers: Dict[str, str],
    config: AzureDevOpsConfig,
    repo_id: str,
    pull_request_id: int,
    thread_id: int,
    content: str,
) -> int:
    """Post a reply to a thread and return the comment ID.

    Args:
        requests_module: The requests module.
        headers: Auth headers.
        config: Azure DevOps configuration.
        repo_id: Repository ID.
        pull_request_id: PR ID.
        thread_id: Thread ID to reply to.
        content: Reply content.

    Returns:
        Created comment ID.
    """
    comment_url = config.build_api_url(repo_id, "pullRequests", pull_request_id, "threads", thread_id, "comments")
    body = {"content": content, "commentType": "text"}
    response = requests_module.post(comment_url, headers=headers, json=body, timeout=30)
    response.raise_for_status()
    return response.json().get("id", 0)


def _set_thread_status(
    requests_module: Any,
    headers: Dict[str, str],
    config: AzureDevOpsConfig,
    repo_id: str,
    pull_request_id: int,
    thread_id: int,
    status: str,
) -> None:
    """Set a thread's status via PATCH.

    Args:
        requests_module: The requests module.
        headers: Auth headers.
        config: Azure DevOps configuration.
        repo_id: Repository ID.
        pull_request_id: PR ID.
        thread_id: Thread ID.
        status: New status string ("active", "closed", "fixed").
    """
    resolve_thread_by_id(requests_module, headers, config, repo_id, pull_request_id, thread_id, status=status)


def confirm_suggestion_addressed() -> None:
    """Confirm that a previous suggestion was properly addressed.

    Resolves the suggestion thread (if not already resolved) and posts a
    confirmation reply.

    Reads from state:
        - pull_request_id (required): PR ID
        - thread_id (required): Suggestion thread ID
        - suggestion.commit_hash (required): Short commit hash where the fix was applied
        - dry_run (optional): Preview without making API calls

    Usage:
        agdt-set pull_request_id 23046
        agdt-set thread_id 139474
        agdt-set suggestion.commit_hash "abc1234"
        agdt-confirm-suggestion-addressed
    """
    requests = require_requests()

    pull_request_id = get_pull_request_id(required=True)
    thread_id = get_thread_id(required=True)
    commit_hash = get_value("suggestion.commit_hash")
    if not commit_hash:
        print("Error: suggestion.commit_hash is required.", file=sys.stderr)
        print('  agdt-set suggestion.commit_hash "abc1234"', file=sys.stderr)
        sys.exit(1)

    dry_run = is_dry_run()
    config = AzureDevOpsConfig.from_state()

    short_hash = str(commit_hash)[:7]
    reply_content = f"✅ Suggestion addressed in commit `{short_hash}`."

    if dry_run:
        print(f"[DRY RUN] Would confirm suggestion on thread {thread_id} of PR {pull_request_id}")
        print(f"[DRY RUN] Reply: {reply_content}")
        print("[DRY RUN] Would resolve thread (status=closed)")
        return

    pat = get_pat()
    headers = get_auth_headers(pat)

    print(f"Resolving repository ID for '{config.repository}'...")
    repo_id = get_repository_id(config.organization, config.project, config.repository)

    # Post confirmation reply
    print(f"Posting confirmation reply on thread {thread_id}...")
    comment_id = _post_thread_reply(requests, headers, config, repo_id, pull_request_id, thread_id, reply_content)
    print(f"Reply posted (comment ID: {comment_id})")

    # Resolve the thread
    print(f"Resolving thread {thread_id}...")
    _set_thread_status(requests, headers, config, repo_id, pull_request_id, thread_id, "closed")
    print(f"Thread {thread_id} resolved.")


def reject_suggestion_resolution() -> None:
    """Reject a suggestion resolution — the suggestion was not properly addressed.

    Reactivates the thread (if closed/resolved) and posts an explanation reply.

    Reads from state:
        - pull_request_id (required): PR ID
        - thread_id (required): Suggestion thread ID
        - suggestion.explanation (required): Why the suggestion was not addressed
        - dry_run (optional): Preview without making API calls

    Usage:
        agdt-set pull_request_id 23046
        agdt-set thread_id 139474
        agdt-set suggestion.explanation "The null check is still missing on line 42."
        agdt-reject-suggestion-resolution
    """
    requests = require_requests()

    pull_request_id = get_pull_request_id(required=True)
    thread_id = get_thread_id(required=True)
    explanation = get_value("suggestion.explanation")
    if not explanation:
        print("Error: suggestion.explanation is required.", file=sys.stderr)
        print('  agdt-set suggestion.explanation "Reason here"', file=sys.stderr)
        sys.exit(1)

    dry_run = is_dry_run()
    config = AzureDevOpsConfig.from_state()

    reply_content = f"❌ Suggestion not properly addressed: {explanation}"

    if dry_run:
        print(f"[DRY RUN] Would reject suggestion on thread {thread_id} of PR {pull_request_id}")
        print(f"[DRY RUN] Reply: {reply_content}")
        print("[DRY RUN] Would reactivate thread (status=active)")
        return

    pat = get_pat()
    headers = get_auth_headers(pat)

    print(f"Resolving repository ID for '{config.repository}'...")
    repo_id = get_repository_id(config.organization, config.project, config.repository)

    # Post explanation reply
    print(f"Posting rejection reply on thread {thread_id}...")
    comment_id = _post_thread_reply(requests, headers, config, repo_id, pull_request_id, thread_id, reply_content)
    print(f"Reply posted (comment ID: {comment_id})")

    # Reactivate the thread
    print(f"Reactivating thread {thread_id}...")
    _set_thread_status(requests, headers, config, repo_id, pull_request_id, thread_id, "active")
    print(f"Thread {thread_id} reactivated.")
