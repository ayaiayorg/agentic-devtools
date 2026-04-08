"""Analyze Copilot review status for a GitHub pull request.

This module provides the ``agdt-gh-copilot-review-status`` CLI command that
fetches reviews via the ``gh`` CLI REST API, filters to the Copilot reviewer
bot on the current head commit, counts inline and suppressed (minimized)
comments via GraphQL cursor pagination, classifies the review status, and
returns structured JSON to stdout while writing state keys.

Public API
----------
- :func:`get_copilot_review_status` — core function (safe to call from
  other Python code; does **not** call ``sys.exit``).
- :func:`copilot_review_status_command` — CLI entry point.
- :func:`_select_latest_copilot_review` — exported for sibling commands.
- :func:`_classify_review_status` — exported for sibling commands.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

from ...state import get_value, set_value
from ..subprocess_utils import run_safe
from .repo_resolution import resolve_github_repo

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COPILOT_REVIEWER_LOGIN = "copilot-pull-request-reviewer[bot]"

_SUPPRESSED_COMMENTS_QUERY = """
query($reviewNodeId: ID!, $commentsCursor: String) {
  node(id: $reviewNodeId) {
    ... on PullRequestReview {
      comments(first: 100, after: $commentsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes { isMinimized }
      }
    }
  }
}
"""

_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 10

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fetch_reviews_for_pr(pr_number: int, repo: str) -> list[dict[str, Any]]:
    """Fetch all reviews for a pull request via paginated REST API.

    Args:
        pr_number: Pull request number.
        repo: Repository in ``owner/repo`` format.

    Returns:
        List of review objects.

    Raises:
        RuntimeError: When all retry attempts are exhausted.
    """
    cmd = [
        "gh",
        "api",
        f"repos/{repo}/pulls/{pr_number}/reviews",
        "--paginate",
        "--jq",
        ".[]",
    ]

    last_error = ""
    for attempt in range(_MAX_RETRIES):
        try:
            result = run_safe(cmd, capture_output=True, text=True, shell=False)
        except OSError as exc:
            last_error = str(exc)
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAY_SECONDS)
            continue
        if result.returncode == 0:
            stdout = result.stdout.strip()
            if not stdout:
                return []
            reviews: list[dict[str, Any]] = []
            for line in stdout.splitlines():
                line = line.strip()
                if line:
                    try:
                        reviews.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        raise RuntimeError(
                            f"Failed to parse review JSON from GitHub API for PR #{pr_number} in {repo}: {exc}"
                        ) from exc
            return reviews

        last_error = (result.stderr or result.stdout or "").strip()
        if attempt < _MAX_RETRIES - 1:
            time.sleep(_RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"Failed to fetch reviews for PR #{pr_number} in {repo} after {_MAX_RETRIES} attempts: {last_error}"
    )


def _select_latest_copilot_review(reviews: list[dict[str, Any]], head_sha: str) -> dict[str, Any] | None:
    """Select the most recent Copilot review matching *head_sha*.

    Filters to reviews where ``user.login`` is the Copilot reviewer bot and
    ``commit_id`` equals *head_sha*.  Sorts by ``submitted_at`` descending
    (newest first), breaking ties by ``id`` descending.

    Returns:
        The most recent matching review dict, or ``None``.
    """
    filtered: list[dict[str, Any]] = []
    for r in reviews:
        user = r.get("user")
        if not isinstance(user, dict):
            continue
        if user.get("login") == COPILOT_REVIEWER_LOGIN and r.get("commit_id") == head_sha:
            filtered.append(r)
    if not filtered:
        return None

    filtered.sort(
        key=lambda r: (r.get("submitted_at") or "", r.get("id", 0)),
        reverse=True,
    )
    return filtered[0]


def _count_inline_comments(pr_number: int, repo: str, review_id: int) -> int:
    """Count inline comments (with non-empty body) for a review.

    Raises:
        RuntimeError: When all retry attempts are exhausted.
    """
    cmd = [
        "gh",
        "api",
        f"repos/{repo}/pulls/{pr_number}/reviews/{review_id}/comments",
        "--paginate",
        "--jq",
        ".[]",
    ]

    last_error = ""
    for attempt in range(_MAX_RETRIES):
        try:
            result = run_safe(cmd, capture_output=True, text=True, shell=False)
        except OSError as exc:
            last_error = str(exc)
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAY_SECONDS)
            continue
        if result.returncode == 0:
            stdout = result.stdout.strip()
            if not stdout:
                return 0
            count = 0
            for line in stdout.splitlines():
                line = line.strip()
                if line:
                    try:
                        comment = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise RuntimeError(
                            f"Failed to parse inline comment JSON from GitHub API for "
                            f"review {review_id} on PR #{pr_number} in {repo}: {exc}"
                        ) from exc
                    if (comment.get("body") or "").strip():
                        count += 1
            return count

        last_error = (result.stderr or result.stdout or "").strip()
        if attempt < _MAX_RETRIES - 1:
            time.sleep(_RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"Failed to fetch inline comments for review {review_id} on "
        f"PR #{pr_number} in {repo} after {_MAX_RETRIES} attempts: {last_error}"
    )


def _count_suppressed_comments(review_node_id: str) -> int:
    """Count minimized (suppressed) comments via GraphQL cursor pagination.

    If the review node is missing or has no ``comments`` field the function
    returns the suppressed count accumulated so far with a warning to stderr.

    Raises:
        RuntimeError: When all retry attempts for a page are exhausted or
            when the GraphQL response cannot be parsed as JSON.
    """
    if not review_node_id:
        print(
            "Warning: empty review node_id — skipping suppressed comment count.",
            file=sys.stderr,
        )
        return 0

    cursor: str | None = None
    suppressed_count = 0

    while True:
        gql_vars = ["-f", f"reviewNodeId={review_node_id}"]
        if cursor is not None:
            gql_vars += ["-f", f"commentsCursor={cursor}"]

        cmd = [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={_SUPPRESSED_COMMENTS_QUERY}",
            *gql_vars,
        ]

        last_error = ""
        response_data: dict[str, Any] | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                result = run_safe(cmd, capture_output=True, text=True, shell=False)
            except OSError as exc:
                last_error = str(exc)
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_DELAY_SECONDS)
                continue
            if result.returncode == 0:
                try:
                    response_data = json.loads(result.stdout)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"Failed to parse GraphQL response for suppressed comments of review {review_node_id}: {exc}"
                    ) from exc
                break

            last_error = (result.stderr or result.stdout or "").strip()
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAY_SECONDS)

        if response_data is None:
            raise RuntimeError(
                f"Failed to fetch suppressed comments for review "
                f"{review_node_id} after {_MAX_RETRIES} attempts: {last_error}"
            )

        node = response_data.get("data", {}).get("node")
        if node is None or "comments" not in node:
            print(
                "Warning: review node missing or has no comments field — "
                "returning the suppressed count accumulated so far.",
                file=sys.stderr,
            )
            return suppressed_count

        comments_data = node["comments"]
        for comment_node in comments_data.get("nodes", []):
            if comment_node.get("isMinimized"):
                suppressed_count += 1

        page_info = comments_data.get("pageInfo", {})
        if page_info.get("hasNextPage"):
            next_cursor = page_info.get("endCursor")
            if not next_cursor:
                raise RuntimeError(
                    "GitHub GraphQL pagination indicated more suppressed comment pages "
                    f"for review {review_node_id}, but pageInfo.endCursor was missing or null."
                )
            cursor = next_cursor
        else:
            break

    return suppressed_count


def _classify_review_status(review_state: str, inline_count: int, suppressed_count: int) -> tuple[str, str]:
    """Classify the overall Copilot review status.

    Returns:
        A ``(status, action_required)`` tuple.
    """
    # Feedback check has highest priority
    if inline_count > 0 or suppressed_count > 0:
        return ("has-feedback", "address-copilot-review")

    if review_state == "CHANGES_REQUESTED":
        return ("changes-requested", "address-copilot-review")

    if review_state in ("APPROVED", "COMMENTED"):
        return ("clean", "none")

    return ("unknown-state", "investigate")


# ---------------------------------------------------------------------------
# Core function (no sys.exit)
# ---------------------------------------------------------------------------


def get_copilot_review_status(pr_number: int, repo: str, head_sha: str) -> dict[str, Any]:
    """Analyze the Copilot review status for *pr_number*.

    This function is safe to call from other Python code — it does **not**
    call ``sys.exit()``.  Unrecoverable API errors are raised as
    :class:`RuntimeError`.

    State keys written (``github.*`` namespace):
        - ``github.copilot_review_status``
        - ``github.copilot_review_id``
        - ``github.copilot_review_node_id``
        - ``github.copilot_review_url``

    Returns:
        A dict with structured review analysis.
    """
    reviews = _fetch_reviews_for_pr(pr_number, repo)
    review = _select_latest_copilot_review(reviews, head_sha)

    if review is None:
        result: dict[str, Any] = {
            "prNumber": pr_number,
            "repo": repo,
            "status": "no-review",
            "reviewId": None,
            "reviewNodeId": None,
            "reviewState": None,
            "commitId": head_sha,
            "submittedAt": None,
            "inlineCommentCount": 0,
            "suppressedCommentCount": 0,
            "reviewUrl": None,
            "actionRequired": "wait",
        }
        set_value("github.copilot_review_status", "no-review")
        set_value("github.copilot_review_id", None)
        set_value("github.copilot_review_node_id", None)
        set_value("github.copilot_review_url", None)
        return result

    review_id: int = review["id"]
    review_node_id: str | None = review.get("node_id")
    review_state: str = review.get("state", "")
    submitted_at: str | None = review.get("submitted_at")

    inline_count = _count_inline_comments(pr_number, repo, review_id)

    suppressed_count = 0
    if review_node_id:
        suppressed_count = _count_suppressed_comments(review_node_id)
    else:
        print(
            "Warning: review has no node_id — skipping suppressed comment count.",
            file=sys.stderr,
        )

    status, action_required = _classify_review_status(review_state, inline_count, suppressed_count)

    review_url = f"https://github.com/{repo}/pull/{pr_number}#pullrequestreview-{review_id}"

    result = {
        "prNumber": pr_number,
        "repo": repo,
        "status": status,
        "reviewId": review_id,
        "reviewNodeId": review_node_id,
        "reviewState": review_state,
        "commitId": head_sha,
        "submittedAt": submitted_at,
        "inlineCommentCount": inline_count,
        "suppressedCommentCount": suppressed_count,
        "reviewUrl": review_url,
        "actionRequired": action_required,
    }

    set_value("github.copilot_review_status", status)
    set_value("github.copilot_review_id", review_id)
    set_value("github.copilot_review_node_id", review_node_id)
    set_value("github.copilot_review_url", review_url)

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def copilot_review_status_command() -> None:
    """CLI entry point for ``agdt-gh-copilot-review-status``."""
    parser = argparse.ArgumentParser(
        description="Analyze Copilot review status for a PR",
    )
    parser.add_argument("--pr", type=int, default=None, help="Pull request number")
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="Repository in owner/repo format",
    )
    parser.add_argument(
        "--head-sha",
        type=str,
        default=None,
        help="Head commit SHA to match reviews against",
    )
    args = parser.parse_args()

    # --- resolve pr_number ---
    pr_number = args.pr
    if pr_number is None:
        state_pr = get_value("github.pull_request_number")
        if state_pr is not None:
            try:
                pr_number = int(state_pr)
            except (TypeError, ValueError):
                print(
                    f"Error: state key `github.pull_request_number` has non-numeric value {state_pr!r}. "
                    "Pass --pr with a valid integer or fix the state value.",
                    file=sys.stderr,
                )
                sys.exit(1)
    if pr_number is None:
        print(
            "Error: PR number not available. "
            "Pass --pr or set `github.pull_request_number` with `agdt-set github.pull_request_number <number>`.",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- resolve repo ---
    repo = resolve_github_repo(args.repo)

    # --- resolve head_sha ---
    head_sha = args.head_sha
    if head_sha is None:
        state_sha = get_value("github.head_ref_oid")
        if state_sha is not None:
            head_sha = str(state_sha)
    if head_sha is None:
        print(
            "Error: head SHA not available. "
            "Pass --head-sha or set `github.head_ref_oid` with `agdt-set github.head_ref_oid <sha>`.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        result = get_copilot_review_status(pr_number, repo, head_sha)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, indent=2))
