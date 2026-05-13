"""
Request a Copilot review on a GitHub pull request.

Provides ``request_copilot_review()`` — a synchronous function that POSTs a
review request for the ``copilot-pull-request-reviewer[bot]`` via ``gh api``,
verifies the request was registered by checking the requested reviewers list
and the reviews list (in case the bot already started reviewing), and retries
verification up to 3 times with exponential backoff.

CLI entry point: ``agdt-gh-request-copilot-review``
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time

from ...state import get_value, set_value
from ..subprocess_utils import run_safe
from .repo_resolution import _validate_repo_format, resolve_github_repo

# The GitHub login for the Copilot pull-request reviewer bot.
# TODO: consolidate with copilot_review_status.py when #1120 is implemented.
COPILOT_REVIEWER_LOGIN = "copilot-pull-request-reviewer[bot]"

# Retry configuration for verification polling.
_MAX_VERIFY_RETRIES = 3
_INITIAL_BACKOFF_SECONDS = 2.0


def _login_matches(login: str) -> bool:
    """Return ``True`` if *login* matches the Copilot reviewer bot (case-insensitive)."""
    return login.lower() == COPILOT_REVIEWER_LOGIN.lower()


def _check_login_in_response(data: dict) -> bool:
    """Return ``True`` if the Copilot bot appears in a requested-reviewers response.

    The GitHub API returns both ``users`` and ``teams`` arrays.  Bot accounts
    typically appear in ``users``, but we check both for robustness.
    """
    for user in data.get("users", []):
        if _login_matches(user.get("login", "")):
            return True
    for team in data.get("teams", []):
        if _login_matches(team.get("slug", "")):
            return True
    return False


def _post_review_request(
    pr_number: int,
    owner: str,
    repo_name: str,
) -> tuple[bool, str | None, bool]:
    """POST a review request for the Copilot bot.

    Args:
        pr_number: Pull request number.
        owner: Repository owner.
        repo_name: Repository name (without owner prefix).

    Returns:
        A 3-tuple ``(posted, error_message, immediate_verified)``.

        * ``posted`` — ``True`` when the HTTP request succeeded.
        * ``error_message`` — error description on failure, ``None`` on success.
        * ``immediate_verified`` — ``True`` when the POST response body
          already confirms the reviewer is in the requested list.
    """
    result = run_safe(
        [
            "gh",
            "api",
            f"repos/{owner}/{repo_name}/pulls/{pr_number}/requested_reviewers",
            "-X",
            "POST",
            "-f",
            f"reviewers[]={COPILOT_REVIEWER_LOGIN}",
        ],
        capture_output=True,
        text=True,
        shell=False,
    )
    if result.returncode != 0:
        return (False, result.stderr.strip() or "Unknown error", False)

    # The successful POST returns the full PR object whose
    # ``requested_reviewers`` field reflects the updated reviewer list.
    immediate_verified = False
    if result.stdout:
        try:
            pr_data = json.loads(result.stdout)
            for reviewer in pr_data.get("requested_reviewers", []):
                if _login_matches(reviewer.get("login", "")):
                    immediate_verified = True
                    break
        except (json.JSONDecodeError, TypeError):
            pass  # non-critical — we still fall back to the polling path

    return (True, None, immediate_verified)


def _verify_reviewer_requested(pr_number: int, owner: str, repo_name: str) -> bool:
    """Check whether the Copilot bot appears in the requested reviewers list.

    Checks both the ``users`` and ``teams`` arrays in the response.

    Args:
        pr_number: Pull request number.
        owner: Repository owner.
        repo_name: Repository name (without owner prefix).

    Returns:
        ``True`` if the bot is found, ``False`` otherwise.
    """
    result = run_safe(
        [
            "gh",
            "api",
            f"repos/{owner}/{repo_name}/pulls/{pr_number}/requested_reviewers",
        ],
        capture_output=True,
        text=True,
        shell=False,
    )
    if result.returncode != 0:
        print(
            f"Warning: verification API call failed: {result.stderr.strip()}",
            file=sys.stderr,
        )
        return False

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(
            "Warning: could not parse verification response as JSON.",
            file=sys.stderr,
        )
        return False

    return _check_login_in_response(data)


def _check_reviewer_in_reviews(pr_number: int, owner: str, repo_name: str) -> bool:
    """Fallback: check whether the Copilot bot has already submitted a review.

    When the bot processes a review request very quickly it may leave the
    ``requested_reviewers`` list before our verification poll runs.  In that
    case we check the ``reviews`` endpoint to see if the bot has already
    started or completed a review.

    Args:
        pr_number: Pull request number.
        owner: Repository owner.
        repo_name: Repository name (without owner prefix).

    Returns:
        ``True`` if the bot has at least one review entry, ``False`` otherwise.
    """
    result = run_safe(
        [
            "gh",
            "api",
            f"repos/{owner}/{repo_name}/pulls/{pr_number}/reviews",
        ],
        capture_output=True,
        text=True,
        shell=False,
    )
    if result.returncode != 0:
        print(
            f"Warning: reviews API call failed: {result.stderr.strip()}",
            file=sys.stderr,
        )
        return False

    try:
        reviews = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        print(
            "Warning: could not parse reviews response as JSON.",
            file=sys.stderr,
        )
        return False

    if not isinstance(reviews, list):
        return False

    for review in reviews:
        user = review.get("user") or {}
        if _login_matches(user.get("login", "")):
            return True
    return False


def request_copilot_review(pr_number: int, repo: str) -> dict:
    """Request a Copilot review and verify it was registered.

    Verification strategy (in order):

    1. **POST response** — the successful POST returns the updated PR object;
       if the bot appears in ``requested_reviewers`` we are done immediately.
    2. **Requested-reviewers polling** — GET the requested reviewers list with
       exponential back-off (up to ``_MAX_VERIFY_RETRIES`` retries).
    3. **Reviews fallback** — if the bot already started reviewing it will no
       longer be in ``requested_reviewers`` but will appear in the reviews
       list.

    Args:
        pr_number: Pull request number.
        repo: Repository in ``owner/repo`` format.

    Returns:
        Result dict with keys: ``prNumber``, ``repo``, ``requested``,
        ``reviewer``, ``verified``, ``retries``, and optionally ``error``
        and ``message``.
    """
    validated = _validate_repo_format(repo)
    if validated is None:
        print(
            f"Error: repo must be in 'owner/repo' format, got: {repo!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not shutil.which("gh"):
        print(
            "Error: 'gh' CLI is not installed or not on PATH. Install from https://cli.github.com/",
            file=sys.stderr,
        )
        sys.exit(1)

    owner, repo_name = validated.split("/")

    # --- POST the review request ---
    posted, error_msg, immediate_verified = _post_review_request(pr_number, owner, repo_name)

    if not posted:
        result = {
            "prNumber": pr_number,
            "repo": repo,
            "requested": False,
            "reviewer": COPILOT_REVIEWER_LOGIN,
            "error": "request_failed",
            "message": error_msg,
            "verified": False,
            "retries": 0,
        }
        set_value("github.copilot_review_requested", False)
        set_value("github.copilot_review_request_verified", False)
        return result

    # --- Fast path: POST response already confirms the reviewer ---
    if immediate_verified:
        result = {
            "prNumber": pr_number,
            "repo": repo,
            "requested": True,
            "reviewer": COPILOT_REVIEWER_LOGIN,
            "verified": True,
            "retries": 0,
        }
        set_value("github.copilot_review_requested", True)
        set_value("github.copilot_review_request_verified", True)
        return result

    # --- Poll the requested-reviewers endpoint with exponential back-off ---
    verified = _verify_reviewer_requested(pr_number, owner, repo_name)
    retries = 0

    while not verified and retries < _MAX_VERIFY_RETRIES:
        delay = _INITIAL_BACKOFF_SECONDS * (2**retries)
        time.sleep(delay)
        retries += 1
        print(
            f"Verification retry {retries}/{_MAX_VERIFY_RETRIES}...",
            file=sys.stderr,
        )
        verified = _verify_reviewer_requested(pr_number, owner, repo_name)

    # --- Fallback: check whether the bot already submitted a review ---
    if not verified:
        print(
            "Requested-reviewers verification exhausted; "
            "checking reviews endpoint as fallback...",
            file=sys.stderr,
        )
        verified = _check_reviewer_in_reviews(pr_number, owner, repo_name)

    result = {
        "prNumber": pr_number,
        "repo": repo,
        "requested": True,
        "reviewer": COPILOT_REVIEWER_LOGIN,
        "verified": verified,
        "retries": retries,
    }
    set_value("github.copilot_review_requested", True)
    set_value("github.copilot_review_request_verified", verified)
    return result


def request_copilot_review_command() -> None:
    """CLI entry point for ``agdt-gh-request-copilot-review``."""
    parser = argparse.ArgumentParser(
        description="Request a Copilot review on a GitHub PR",
    )
    parser.add_argument("--pr", type=int, default=None, help="Pull request number")
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="Repository in owner/repo format",
    )
    args = parser.parse_args()

    # Resolve PR number
    pr_number = args.pr
    if pr_number is None:
        state_pr = get_value("github.pull_request_number")
        if state_pr is None:
            print(
                "Error: --pr is required or set github.pull_request_number in state.",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            pr_number = int(state_pr)
        except (ValueError, TypeError):
            print(
                f"Error: github.pull_request_number must be an integer pull request number, got: {state_pr!r}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Resolve repo
    repo = resolve_github_repo(args.repo)

    result = request_copilot_review(pr_number, repo)
    print(json.dumps(result, indent=2))
