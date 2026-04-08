"""
Request a Copilot review on a GitHub pull request.

Provides ``request_copilot_review()`` — a synchronous function that POSTs a
review request for the ``copilot-pull-request-reviewer[bot]`` via ``gh api``,
verifies the request was registered by checking the requested reviewers list,
and retries verification up to 2 times with a 5-second delay.

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


def _post_review_request(pr_number: int, owner: str, repo_name: str) -> tuple[bool, str | None]:
    """POST a review request for the Copilot bot.

    Args:
        pr_number: Pull request number.
        owner: Repository owner.
        repo_name: Repository name (without owner prefix).

    Returns:
        ``(True, None)`` on success, ``(False, error_message)`` on failure.
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
    if result.returncode == 0:
        return (True, None)
    return (False, result.stderr.strip() or "Unknown error")


def _verify_reviewer_requested(pr_number: int, owner: str, repo_name: str) -> bool:
    """Check whether the Copilot bot appears in the requested reviewers list.

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

    for user in data.get("users", []):
        if user.get("login", "").lower() == COPILOT_REVIEWER_LOGIN.lower():
            return True
    return False


def request_copilot_review(pr_number: int, repo: str) -> dict:
    """Request a Copilot review and verify it was registered.

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
    posted, error_msg = _post_review_request(pr_number, owner, repo_name)

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

    # --- Verify the reviewer appears in the requested list ---
    verified = _verify_reviewer_requested(pr_number, owner, repo_name)
    retries = 0

    while not verified and retries < 2:
        time.sleep(5.0)
        retries += 1
        print(f"Verification retry {retries}/2...", file=sys.stderr)
        verified = _verify_reviewer_requested(pr_number, owner, repo_name)

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
