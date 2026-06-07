"""Post replies to GitHub PR review comments with verification and retry.

Provides the ``agdt-gh-reply-to-review-comments`` CLI command that:

1. Reads a JSON file of ``{commentId, body}`` entries
2. Posts each reply via ``gh api``
3. Batch-verifies all replies by checking ``in_reply_to_id``
4. Retries failed replies up to 2 times
5. Returns structured JSON to stdout
"""

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from ...state import get_value, set_value
from ..subprocess_utils import run_safe
from .repo_resolution import resolve_github_repo

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_MAX_RETRIES = 2
_RETRY_DELAY = 3.0


def _check_gh_available() -> None:
    """Verify ``gh`` CLI is installed, or exit with a helpful error."""
    if shutil.which("gh") is None:
        print(
            "Error: 'gh' CLI is not installed or not on PATH. Install from https://cli.github.com/",
            file=sys.stderr,
        )
        sys.exit(1)


def _load_replies_file(file_path: str) -> list[dict]:
    """Read and parse the replies JSON file.

    Parameters
    ----------
    file_path:
        Path to a JSON file containing an array of reply entries.

    Returns
    -------
    list[dict]
        Parsed list of reply entry dicts.

    Raises
    ------
    SystemExit
        On file-not-found, JSON parse error, or non-array content.
    """
    try:
        text = Path(file_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: Replies file not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError:
        print(
            f"Error: Replies file is not valid UTF-8 text: {file_path}",
            file=sys.stderr,
        )
        sys.exit(1)
    except OSError as exc:
        print(
            f"Error: Failed to read replies file '{file_path}': {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        print(
            f"Error: Failed to parse replies file as JSON: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not isinstance(data, list):
        print("Error: Replies file must contain a JSON array", file=sys.stderr)
        sys.exit(1)

    return data


def _validate_reply_entries(entries: list[dict]) -> None:
    """Validate that each entry has the required fields.

    Parameters
    ----------
    entries:
        List of reply dicts to validate.

    Raises
    ------
    SystemExit
        When an entry is missing ``commentId`` or ``body``, when
        ``commentId`` is not an integer, or when ``commentId`` values
        are not unique.
    """
    seen_ids: set[int] = set()
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            print(
                f"Error: Reply entry at index {i} must be a JSON object, got {type(entry).__name__}",
                file=sys.stderr,
            )
            sys.exit(1)
        if "commentId" not in entry:
            print(
                f"Error: Reply entry at index {i} is missing required field 'commentId'",
                file=sys.stderr,
            )
            sys.exit(1)
        comment_id = entry["commentId"]
        if isinstance(comment_id, bool) or not isinstance(comment_id, int):
            print(
                f"Error: Reply entry at index {i}: 'commentId' must be an integer (boolean values are not allowed)",
                file=sys.stderr,
            )
            sys.exit(1)
        if comment_id in seen_ids:
            print(
                f"Error: Reply entry at index {i}: duplicate commentId {comment_id}",
                file=sys.stderr,
            )
            sys.exit(1)
        seen_ids.add(comment_id)
        if "body" not in entry:
            print(
                f"Error: Reply entry at index {i} is missing required field 'body'",
                file=sys.stderr,
            )
            sys.exit(1)
        if not isinstance(entry["body"], str):
            print(
                f"Error: Reply entry at index {i}: 'body' must be a string, got {type(entry['body']).__name__}",
                file=sys.stderr,
            )
            sys.exit(1)
        if not entry["body"].strip():
            print(
                f"Error: Reply entry at index {i}: 'body' must not be empty or whitespace-only",
                file=sys.stderr,
            )
            sys.exit(1)


def _post_single_reply(
    repo: str,
    pr_number: int,
    comment_id: int,
    body: str,
) -> dict | None:
    """Post a single reply to a review comment.

    Returns the parsed response dict on success, or ``None`` on failure.
    """
    result = run_safe(
        [
            "gh",
            "api",
            f"repos/{repo}/pulls/{pr_number}/comments/{comment_id}/replies",
            "--raw-field",
            f"body={body}",
        ],
        capture_output=True,
        text=True,
        shell=False,
    )

    if result.returncode != 0:
        error = result.stderr.strip() if result.stderr else "unknown error"
        print(
            f"Posting reply to comment {comment_id}... FAILED: {error}",
            file=sys.stderr,
        )
        return None

    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(
            f"Posting reply to comment {comment_id}... FAILED: invalid JSON response",
            file=sys.stderr,
        )
        return None

    reply_id = response.get("id")
    print(
        f"Posting reply to comment {comment_id}... OK (reply ID: {reply_id})",
        file=sys.stderr,
    )
    return response


def _verify_replies(
    repo: str,
    pr_number: int,
    expected_comment_ids: list[int],
    expected_reply_map: dict[int, int] | None = None,
) -> dict[int, bool]:
    """Batch-verify that replies exist for the given comment IDs.

    Fetches all review comments and checks that our specific replies
    exist.  When *expected_reply_map* is provided (mapping comment ID
    to the reply ID we received from the API), verification requires
    both a matching ``id`` **and** ``in_reply_to_id``.  Without the
    map, falls back to checking ``in_reply_to_id`` presence only.

    Returns a dict mapping each expected comment ID to ``True``/``False``.
    """
    if not expected_comment_ids:
        return {}

    result = run_safe(
        [
            "gh",
            "api",
            "--paginate",
            f"repos/{repo}/pulls/{pr_number}/comments",
            "--jq",
            ".[] | {id, in_reply_to_id}",
        ],
        capture_output=True,
        text=True,
        shell=False,
    )

    if result.returncode != 0:
        error = result.stderr.strip() if result.stderr else "unknown error"
        print(
            f"Verification fetch failed: {error}",
            file=sys.stderr,
        )
        return {cid: False for cid in expected_comment_ids}

    comments: list[dict] = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            comments.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    reply_to_ids = {c.get("in_reply_to_id") for c in comments if c.get("in_reply_to_id")}

    if expected_reply_map:
        # Build precise lookup: (id, in_reply_to_id) pairs
        comment_pairs = {(c.get("id"), c.get("in_reply_to_id")) for c in comments}
        verification: dict[int, bool] = {}
        for cid in expected_comment_ids:
            reply_id = expected_reply_map.get(cid)
            if reply_id is not None:
                # Verify the specific reply we posted exists
                verification[cid] = (reply_id, cid) in comment_pairs
            else:
                # No known reply ID; fall back to presence check
                verification[cid] = cid in reply_to_ids
        return verification

    return {cid: (cid in reply_to_ids) for cid in expected_comment_ids}


def _retry_failed_replies(
    repo: str,
    pr_number: int,
    review_id: int,
    failed_entries: list[dict],
    max_retries: int = _MAX_RETRIES,
    retry_delay: float = _RETRY_DELAY,
) -> tuple[list[dict], list[dict]]:
    """Retry posting and verifying failed replies.

    Separates retry strategies to avoid creating duplicate replies:
    - Entries that failed to post (``error == "post failed"``) are re-posted
      and then verified.
    - Entries that posted successfully but failed verification
      (``error == "verification failed"``) are only re-verified, not
      re-posted.

    Parameters
    ----------
    failed_entries:
        Each dict must contain ``commentId``, ``body``, and ``error``.
    max_retries:
        Maximum retry cycles.
    retry_delay:
        Seconds to wait between retry cycles.

    Returns
    -------
    tuple[list[dict], list[dict]]
        ``(succeeded, still_failed)`` — each item is a detail dict.
    """
    succeeded: list[dict] = []
    remaining = list(failed_entries)

    for attempt in range(max_retries):
        if not remaining:
            break

        if attempt > 0:
            time.sleep(retry_delay)

        # Separate entries by failure type
        need_post = [e for e in remaining if e.get("error") != "verification failed"]
        need_verify_only = [e for e in remaining if e.get("error") == "verification failed"]

        retry_batch: list[dict] = []

        # Re-post entries that failed to post
        for entry in need_post:
            cid = entry["commentId"]
            body = entry["body"]
            print(
                f"Retry {attempt + 1}/{max_retries} for comment {cid} (re-post)...",
                file=sys.stderr,
            )
            resp = _post_single_reply(repo, pr_number, cid, body)
            if resp is None:
                retry_batch.append(entry)
            else:
                retry_batch.append({**entry, "_response": resp})

        # Re-verify entries that posted OK but failed verification
        for entry in need_verify_only:
            cid = entry["commentId"]
            print(
                f"Retry {attempt + 1}/{max_retries} for comment {cid} (re-verify)...",
                file=sys.stderr,
            )
            retry_batch.append(entry)

        # Verify all entries that may have a reply (posted or previously posted)
        ids_to_verify = [e["commentId"] for e in retry_batch]
        retry_reply_map = {}
        for e in retry_batch:
            cid = e["commentId"]
            if "_response" in e and e["_response"].get("id") is not None:
                retry_reply_map[cid] = e["_response"]["id"]
            elif e.get("replyId") is not None:
                retry_reply_map[cid] = e["replyId"]

        verification = _verify_replies(
            repo,
            pr_number,
            ids_to_verify,
            expected_reply_map=retry_reply_map or None,
        )

        still_remaining: list[dict] = []
        for entry in retry_batch:
            cid = entry["commentId"]
            if verification.get(cid, False):
                reply_id = entry.get("_response", {}).get("id") if "_response" in entry else entry.get("replyId")
                succeeded.append(
                    {
                        "commentId": cid,
                        "status": "replied",
                        "replyId": reply_id,
                        "verified": True,
                    }
                )
            else:
                # Preserve "verification failed" when post succeeded but
                # verification hasn't confirmed yet, so the next cycle only
                # re-verifies instead of creating a duplicate reply.  Escalate
                # to "post failed" only when the entry was already verify-only
                # (no _response) and verification still failed.
                posted_this_cycle = "_response" in entry
                clean = {k: v for k, v in entry.items() if k != "_response"}
                clean["error"] = "verification failed" if posted_this_cycle else "post failed"
                if posted_this_cycle and entry["_response"].get("id") is not None:
                    clean["replyId"] = entry["_response"]["id"]
                still_remaining.append(clean)

        remaining = still_remaining

    return succeeded, remaining


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------


def reply_to_review_comments(
    pr_number: int,
    repo: str,
    review_id: int,
    replies_file: str,
) -> dict:
    """Post replies to review comments, verify, retry, and return results.

    This is the main orchestration function.  It loads the replies file,
    validates entries, posts replies, verifies them, retries failures,
    writes state keys, and returns the result dict.
    """
    entries = _load_replies_file(replies_file)
    _validate_reply_entries(entries)

    # --- Post all replies ---
    details: list[dict] = []
    failed_for_retry: list[dict] = []

    for entry in entries:
        cid = entry["commentId"]
        body = entry["body"]
        resp = _post_single_reply(repo, pr_number, cid, body)
        if resp is None:
            details.append(
                {
                    "commentId": cid,
                    "status": "failed",
                    "replyId": None,
                    "verified": False,
                }
            )
            failed_for_retry.append(
                {
                    "commentId": cid,
                    "body": body,
                    "error": "post failed",
                }
            )
        else:
            details.append(
                {
                    "commentId": cid,
                    "status": "replied",
                    "replyId": resp.get("id"),
                    "verified": False,  # will be updated after verification
                }
            )

    # --- Batch verify ---
    posted_ids = [d["commentId"] for d in details if d["status"] == "replied"]
    reply_map = {
        d["commentId"]: d["replyId"] for d in details if d["status"] == "replied" and d.get("replyId") is not None
    }
    verification = _verify_replies(repo, pr_number, posted_ids, expected_reply_map=reply_map or None)

    entry_by_id = {e["commentId"]: e for e in entries}
    for detail in details:
        if detail["status"] == "replied":
            detail["verified"] = verification.get(detail["commentId"], False)
            if not detail["verified"]:
                entry = entry_by_id.get(detail["commentId"], {})
                failed_for_retry.append(
                    {
                        "commentId": detail["commentId"],
                        "body": entry.get("body", ""),
                        "error": "verification failed",
                        "replyId": detail.get("replyId"),
                    }
                )

    # --- Retry failed ---
    retry_succeeded: list[dict] = []
    still_failed: list[dict] = []
    if failed_for_retry:
        retry_succeeded, still_failed = _retry_failed_replies(repo, pr_number, review_id, failed_for_retry)

        # Merge retry successes back into details, preserving existing
        # replyId when the retry result has None (re-verify-only path)
        retry_map = {d["commentId"]: d for d in retry_succeeded}
        for detail in details:
            if detail["commentId"] in retry_map:
                existing_reply_id = detail.get("replyId")
                detail.update(retry_map[detail["commentId"]])
                if detail.get("replyId") is None and existing_reply_id is not None:
                    detail["replyId"] = existing_reply_id

    # --- Build result ---
    successful = sum(1 for d in details if d["status"] == "replied" and d["verified"])
    failed_count = len(details) - successful

    failed_details = [
        {
            "commentId": e["commentId"],
            "error": e.get("error", "unknown"),
            "retryCount": _MAX_RETRIES,
        }
        for e in still_failed
    ]

    result = {
        "prNumber": pr_number,
        "repo": repo,
        "reviewId": review_id,
        "totalReplies": len(entries),
        "successful": successful,
        "failed": failed_count,
        "verified": failed_count == 0,
        "details": details,
        "failedDetails": failed_details,
    }

    # --- Write state keys ---
    set_value("github.review_replies_total", len(entries))
    set_value("github.review_replies_successful", successful)
    set_value("github.review_replies_failed", failed_count)
    set_value("github.review_replies_verified", failed_count == 0)

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def reply_to_review_comments_command() -> None:
    """CLI entry point for ``agdt-gh-reply-to-review-comments``."""
    parser = argparse.ArgumentParser(
        description="Post replies to GitHub PR review comments with verification and retry.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  agdt-gh-reply-to-review-comments --pr 1115 --repo owner/repo \\
      --review-id 4066913338 --replies-file replies.json

  # Or using state:
  agdt-set github.pull_request_number 1115
  agdt-set github.review_id 4066913338
  agdt-set github.replies_file replies.json
  agdt-gh-reply-to-review-comments
""",
    )
    parser.add_argument("--pr", type=int, default=None, help="PR number")
    parser.add_argument("--repo", type=str, default=None, help="owner/repo")
    parser.add_argument("--review-id", type=int, default=None, help="Review ID")
    parser.add_argument("--replies-file", type=str, default=None, help="Path to JSON replies file")

    args = parser.parse_args()

    # Resolve PR number
    pr_number = args.pr if args.pr is not None else get_value("github.pull_request_number")
    if pr_number is None:
        print(
            "Error: PR number required. Provide --pr or set github.pull_request_number in state.",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        pr_number = int(pr_number)
    except (TypeError, ValueError):
        print(
            f"Error: PR number must be an integer, got {pr_number!r}. "
            "Fix with: agdt-set github.pull_request_number 123",
            file=sys.stderr,
        )
        sys.exit(1)

    # Resolve repo
    repo = resolve_github_repo(args.repo)

    # Resolve review ID (also accept github.copilot_review_id for interoperability
    # with agdt-gh-copilot-review-status and agdt-gh-resolve-review-threads)
    if args.review_id is not None:
        review_id = args.review_id
    else:
        review_id = get_value("github.review_id")
        if review_id is None:
            review_id = get_value("github.copilot_review_id")
    if review_id is None:
        print(
            "Error: Review ID required. Provide --review-id or set github.review_id"
            " (or github.copilot_review_id) in state.",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        review_id = int(review_id)
    except (TypeError, ValueError):
        print(
            f"Error: Review ID must be an integer, got {review_id!r}. Fix with: agdt-set github.review_id 123",
            file=sys.stderr,
        )
        sys.exit(1)

    # Resolve replies file
    replies_file = args.replies_file if args.replies_file is not None else get_value("github.replies_file")
    if replies_file is None:
        print(
            "Error: Replies file required. Provide --replies-file or set github.replies_file in state.",
            file=sys.stderr,
        )
        sys.exit(1)

    _check_gh_available()

    result = reply_to_review_comments(pr_number, repo, review_id, str(replies_file))
    print(json.dumps(result, indent=2))
