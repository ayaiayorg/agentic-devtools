"""Resolve GitHub PR review threads via GraphQL.

Provides ``resolve_review_threads_command()`` — a synchronous CLI entry
point that fetches all PR review threads with cursor-based pagination,
maps REST comment ``databaseId`` values to GraphQL thread IDs, resolves
targeted unresolved threads via the ``resolveReviewThread`` mutation,
verifies resolution, and retries failed resolutions up to 2 times.

The result is printed as structured JSON to stdout and key metrics are
written to ``github.*`` state keys.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time

from ...state import get_value, set_value
from ..subprocess_utils import run_safe
from .repo_resolution import resolve_github_repo

# ---------------------------------------------------------------------------
# GraphQL constants
# ---------------------------------------------------------------------------

_REVIEW_THREADS_QUERY = """
query($owner: String!, $repoName: String!, $prNumber: Int!, $threadsCursor: String) {
  repository(owner: $owner, name: $repoName) {
    pullRequest(number: $prNumber) {
      reviewThreads(first: 100, after: $threadsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          comments(first: 100) {
            nodes { databaseId }
          }
        }
      }
    }
  }
}
"""

_RESOLVE_THREAD_MUTATION = """
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread { id isResolved }
  }
}
"""

_MAX_FETCH_RETRIES = 2
_RETRY_DELAY_SECONDS = 10


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fetch_review_comment_ids(
    pr_number: int,
    repo: str,
    review_id: int,
) -> list[int]:
    """Fetch comment database IDs for a specific review via REST API.

    Uses ``gh api --paginate`` so all pages are returned in one call.

    Raises:
        RuntimeError: When all retry attempts are exhausted.
    """
    owner, repo_name = repo.split("/")
    cmd = [
        "gh",
        "api",
        f"repos/{owner}/{repo_name}/pulls/{pr_number}/reviews/{review_id}/comments",
        "--paginate",
        "--jq",
        ".[].id",
    ]

    last_error = ""
    for attempt in range(_MAX_FETCH_RETRIES + 1):
        try:
            result = run_safe(cmd, capture_output=True, text=True, shell=False)
        except OSError as exc:
            last_error = str(exc)
        else:
            if result.returncode == 0:
                stdout = result.stdout.strip()
                if not stdout:
                    return []
                return [int(line.strip()) for line in stdout.splitlines() if line.strip()]
            last_error = result.stderr.strip() or f"exit code {result.returncode}"
        if attempt < _MAX_FETCH_RETRIES:
            time.sleep(_RETRY_DELAY_SECONDS)

    msg = (
        f"Failed to fetch comment IDs for review {review_id} "
        f"on PR #{pr_number} after {_MAX_FETCH_RETRIES + 1} attempts: {last_error}"
    )
    raise RuntimeError(msg)


def _fetch_review_threads(
    pr_number: int,
    owner: str,
    repo_name: str,
) -> list[dict]:
    """Fetch all review threads via paginated GraphQL query.

    Raises:
        RuntimeError: When all retry attempts are exhausted for any page.
    """
    all_threads: list[dict] = []
    cursor: str | None = None

    while True:
        cmd = [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={_REVIEW_THREADS_QUERY}",
            "-f",
            f"owner={owner}",
            "-f",
            f"repoName={repo_name}",
            "-F",
            f"prNumber={pr_number}",
        ]
        if cursor is not None:
            cmd += ["-f", f"threadsCursor={cursor}"]

        last_error = ""
        page_data = None
        for attempt in range(_MAX_FETCH_RETRIES + 1):
            try:
                result = run_safe(cmd, capture_output=True, text=True, shell=False)
            except OSError as exc:
                last_error = str(exc)
            else:
                if result.returncode == 0:
                    try:
                        response = json.loads(result.stdout)
                        page_data = response["data"]["repository"]["pullRequest"]["reviewThreads"]
                        break
                    except (json.JSONDecodeError, KeyError, TypeError) as exc:
                        last_error = str(exc)
                else:
                    last_error = result.stderr.strip() or f"exit code {result.returncode}"
            if attempt < _MAX_FETCH_RETRIES:
                time.sleep(_RETRY_DELAY_SECONDS)

        if page_data is None:
            msg = (
                f"Failed to fetch review threads for PR #{pr_number} "
                f"after {_MAX_FETCH_RETRIES + 1} attempts: {last_error}"
            )
            raise RuntimeError(msg)

        all_threads.extend(page_data["nodes"])

        page_info = page_data["pageInfo"]
        if page_info["hasNextPage"]:
            end_cursor = page_info["endCursor"]
            if not end_cursor:
                msg = (
                    f"GitHub reviewThreads pagination for PR #{pr_number} reported "
                    "hasNextPage=True but did not provide an endCursor"
                )
                raise RuntimeError(msg)
            cursor = end_cursor
        else:
            break

    return all_threads


def _map_comments_to_threads(
    threads: list[dict],
    target_comment_ids: set[int],
) -> list[dict]:
    """Map target comment database IDs to their parent thread info.

    Pure function — no subprocess calls.
    """
    result: list[dict] = []
    for thread in threads:
        comment_nodes = thread.get("comments", {}).get("nodes", [])
        if not comment_nodes:
            continue
        for node in comment_nodes:
            database_id = node.get("databaseId")
            if database_id is not None and database_id in target_comment_ids:
                result.append(
                    {
                        "threadId": thread["id"],
                        "commentId": database_id,
                        "isResolved": thread["isResolved"],
                    }
                )
                break
    return result


def _resolve_thread(thread_id: str) -> bool:
    """Resolve a single review thread via GraphQL mutation.

    Returns ``True`` if the thread is resolved after the call, ``False``
    otherwise (including on errors).
    """
    cmd = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={_RESOLVE_THREAD_MUTATION}",
        "-f",
        f"threadId={thread_id}",
    ]
    try:
        result = run_safe(cmd, capture_output=True, text=True, shell=False)
    except OSError as exc:
        print(
            f"Warning: resolveReviewThread failed for {thread_id}: {exc}",
            file=sys.stderr,
        )
        return False
    if result.returncode != 0:
        print(
            f"Warning: resolveReviewThread mutation failed for {thread_id}: {result.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    try:
        data = json.loads(result.stdout)
        return bool(data["data"]["resolveReviewThread"]["thread"]["isResolved"])
    except (json.JSONDecodeError, KeyError, TypeError):
        print(
            f"Warning: unexpected mutation response for {thread_id}",
            file=sys.stderr,
        )
        return False


def _resolve_and_verify(
    pr_number: int,
    owner: str,
    repo_name: str,
    target_comment_ids: set[int],
    max_retries: int = 2,
) -> dict:
    """Orchestrate the full resolve → verify → retry cycle."""
    # --- initial fetch & map ---
    threads = _fetch_review_threads(pr_number, owner, repo_name)
    mapped = _map_comments_to_threads(threads, target_comment_ids)

    already_resolved = [t for t in mapped if t["isResolved"]]
    to_resolve = [t for t in mapped if not t["isResolved"]]

    # Track per-thread final status
    status_map: dict[str, dict] = {}
    for t in already_resolved:
        status_map[t["threadId"]] = {
            "threadId": t["threadId"],
            "commentId": t["commentId"],
            "status": "already_resolved",
        }

    # --- first resolution pass ---
    still_pending: list[dict] = []
    for t in to_resolve:
        ok = _resolve_thread(t["threadId"])
        if ok:
            status_map[t["threadId"]] = {
                "threadId": t["threadId"],
                "commentId": t["commentId"],
                "status": "resolved",
            }
        else:
            still_pending.append(t)

    # --- verification + retry loop ---
    for _retry in range(max_retries):
        if not still_pending:
            break

        # Re-fetch threads and check which ones remain unresolved
        threads = _fetch_review_threads(pr_number, owner, repo_name)
        refreshed = _map_comments_to_threads(threads, target_comment_ids)
        refreshed_map = {t["threadId"]: t for t in refreshed}

        next_pending: list[dict] = []
        for t in still_pending:
            rt = refreshed_map.get(t["threadId"])
            if rt and rt["isResolved"]:
                # Resolved since last check (perhaps eventual consistency)
                status_map[t["threadId"]] = {
                    "threadId": t["threadId"],
                    "commentId": t["commentId"],
                    "status": "resolved",
                }
            else:
                # Still unresolved — retry mutation
                ok = _resolve_thread(t["threadId"])
                if ok:
                    status_map[t["threadId"]] = {
                        "threadId": t["threadId"],
                        "commentId": t["commentId"],
                        "status": "resolved",
                    }
                else:
                    next_pending.append(t)
        still_pending = next_pending

    # --- mark remaining as failed ---
    for t in still_pending:
        status_map[t["threadId"]] = {
            "threadId": t["threadId"],
            "commentId": t["commentId"],
            "status": "failed",
            "error": "Thread still unresolved after retries",
        }

    # --- build result ---
    details = list(status_map.values())
    threads_resolved = sum(1 for d in details if d["status"] == "resolved")
    threads_failed = sum(1 for d in details if d["status"] == "failed")
    already_resolved_count = sum(1 for d in details if d["status"] == "already_resolved")

    return {
        "threadsResolved": threads_resolved,
        "threadsFailed": threads_failed,
        "alreadyResolved": already_resolved_count,
        "totalTargeted": len(details),
        "details": details,
        "verified": threads_failed == 0,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_review_threads(
    pr_number: int,
    repo: str,
    review_id: int | None = None,
    comment_ids: list[int] | None = None,
) -> dict:
    """Resolve targeted review threads on a GitHub PR.

    Either *review_id* or *comment_ids* must be provided.

    Returns a result dict with ``threadsResolved``, ``threadsFailed``,
    ``alreadyResolved``, ``totalTargeted``, ``details``, and ``verified``.

    Raises:
        ValueError: If neither *review_id* nor *comment_ids* is given.
        RuntimeError: On unrecoverable fetch failures.
    """
    owner, repo_name = repo.split("/")

    # Determine target comment IDs
    if comment_ids is not None:
        target_comment_ids = comment_ids
    elif review_id is not None:
        target_comment_ids = _fetch_review_comment_ids(pr_number, repo, review_id)
    else:
        msg = "Either review_id or comment_ids must be provided"
        raise ValueError(msg)

    # Early return when there are no comments to resolve
    if not target_comment_ids:
        result: dict = {
            "prNumber": pr_number,
            "repo": repo,
            "threadsResolved": 0,
            "threadsFailed": 0,
            "alreadyResolved": 0,
            "totalTargeted": 0,
            "details": [],
            "verified": True,
        }
        set_value("github.threads_resolved_count", 0)
        set_value("github.threads_failed_count", 0)
        set_value("github.threads_already_resolved_count", 0)
        set_value("github.threads_resolution_verified", True)
        return result

    result = _resolve_and_verify(pr_number, owner, repo_name, set(target_comment_ids))
    result["prNumber"] = pr_number
    result["repo"] = repo

    # Persist summary to state
    set_value("github.threads_resolved_count", result["threadsResolved"])
    set_value("github.threads_failed_count", result["threadsFailed"])
    set_value("github.threads_already_resolved_count", result["alreadyResolved"])
    set_value("github.threads_resolution_verified", result["verified"])

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def resolve_review_threads_command() -> None:
    """CLI entry point for ``agdt-gh-resolve-review-threads``."""
    parser = argparse.ArgumentParser(
        description="Resolve GitHub PR review threads via GraphQL.",
    )
    parser.add_argument("--pr", type=int, default=None, help="PR number")
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="GitHub repository in owner/repo format",
    )
    parser.add_argument(
        "--review-id",
        type=int,
        default=None,
        help="Review ID to resolve all threads for",
    )
    parser.add_argument(
        "--comment-ids",
        type=str,
        default=None,
        help="Comma-separated comment database IDs to resolve",
    )
    args = parser.parse_args()

    # Preflight: ensure gh CLI is available
    if not shutil.which("gh"):
        print(
            "Error: 'gh' CLI is not installed or not on PATH.\n"
            "Install it from https://cli.github.com/ and authenticate with 'gh auth login'.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Parse comment IDs from comma-separated string
    comment_ids: list[int] | None = None
    if args.comment_ids:
        try:
            comment_ids = [int(x.strip()) for x in args.comment_ids.split(",") if x.strip()]
        except ValueError:
            print(
                "Error: --comment-ids must be a comma-separated list of integers.",
                file=sys.stderr,
            )
            sys.exit(1)
        if not comment_ids:
            print(
                "Error: --comment-ids was provided but resolved to an empty list.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Resolve PR number
    pr_number = args.pr
    if pr_number is None:
        state_val = get_value("github.pull_request_number")
        if state_val is not None:
            try:
                pr_number = int(state_val)
            except (TypeError, ValueError):
                print(
                    "Error: github.pull_request_number in state must be an integer. Pass --pr or fix the state key.",
                    file=sys.stderr,
                )
                sys.exit(1)
    if pr_number is None:
        print(
            "Error: PR number is required. Provide --pr or set github.pull_request_number in state.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Resolve repo
    repo = resolve_github_repo(args.repo)

    # Resolve review ID
    review_id = args.review_id
    if review_id is None:
        state_val = get_value("github.copilot_review_id")
        if state_val is not None:
            try:
                review_id = int(state_val)
            except (TypeError, ValueError):
                print(
                    "Error: github.copilot_review_id in state must be an integer. "
                    "Pass --review-id or fix the state key.",
                    file=sys.stderr,
                )
                sys.exit(1)

    # Validate: need at least one of review_id or comment_ids
    if review_id is None and not comment_ids:
        print(
            "Error: Either --review-id or --comment-ids must be provided.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        result = resolve_review_threads(pr_number, repo, review_id, comment_ids)
    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, indent=2))
