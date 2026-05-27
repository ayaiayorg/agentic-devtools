"""
Approve a GitHub PR with built-in verification and retry.

Submits a PR approval via ``gh pr review --approve``, resolves the
authenticated user's login, verifies the approval was registered by
querying the reviews API, and retries verification up to 2 times.

Returns structured JSON to stdout and writes state keys for downstream
commands.
"""

import argparse
import json
import shutil
import sys
import time

from ...state import get_value, set_value
from ..subprocess_utils import run_safe
from .repo_resolution import resolve_github_repo

_DEFAULT_APPROVAL_BODY = "Approved via agdt-gh-pr-approve"


def _check_gh_available() -> None:
    """Verify ``gh`` CLI is installed, or exit with a helpful error."""
    if shutil.which("gh") is None:
        print(
            "Error: 'gh' CLI is not installed or not on PATH. Install from https://cli.github.com/",
            file=sys.stderr,
        )
        sys.exit(1)


def _resolve_current_user() -> str:
    """Resolve the authenticated GitHub user's login.

    Returns:
        The login string (e.g. ``"acmarsnik"``).

    Raises:
        SystemExit: If the user cannot be resolved.
    """
    result = run_safe(
        ["gh", "api", "user", "--jq", ".login"],
        capture_output=True,
        text=True,
        shell=False,
    )
    login = result.stdout.strip() if result.returncode == 0 else ""
    if not login:
        gh_error_detail = (result.stderr or result.stdout).strip()
        if gh_error_detail:
            print(
                "Error: Could not resolve current GitHub user. "
                f"Ensure 'gh auth login' has been run. gh error: {gh_error_detail}",
                file=sys.stderr,
            )
        else:
            print(
                "Error: Could not resolve current GitHub user. "
                "Ensure 'gh auth login' has been run. "
                f"gh exited with code {result.returncode}.",
                file=sys.stderr,
            )
        sys.exit(1)
    return login


def _submit_approval(
    pr_number: int,
    repo: str,
    body: str,
) -> tuple[bool, str]:
    """Submit a PR approval via ``gh pr review --approve``.

    Args:
        pr_number: The pull request number.
        repo: ``owner/repo`` string.
        body: Approval comment body.

    Returns:
        ``(True, "")`` on success, ``(False, error_message)`` on failure.
    """
    result = run_safe(
        [
            "gh",
            "pr",
            "review",
            str(pr_number),
            "--repo",
            repo,
            "--approve",
            "--body",
            body,
        ],
        capture_output=True,
        text=True,
        shell=False,
    )
    if result.returncode == 0:
        return (True, "")
    error_message = (result.stderr or result.stdout).strip()
    if not error_message:
        error_message = f"gh pr review failed with exit code {result.returncode}"
    return (False, error_message)


def _validate_repo_format(repo: str) -> tuple[str, str]:
    """Validate and split ``owner/repo`` into its components.

    Args:
        repo: The ``owner/repo`` string to validate.

    Returns:
        ``(owner, repo_name)`` tuple.

    Raises:
        SystemExit: If *repo* is not in valid ``owner/repo`` format.
    """
    normalized_repo = repo.strip()
    if normalized_repo.endswith(".git"):
        normalized_repo = normalized_repo[:-4]

    if normalized_repo.count("/") != 1:
        print(
            f"Error: Invalid repo format '{repo}'. Expected 'owner/repo'.",
            file=sys.stderr,
        )
        sys.exit(1)

    owner, repo_name = (part.strip() for part in normalized_repo.split("/"))
    if not owner or not repo_name:
        print(
            f"Error: Invalid repo format '{repo}'. Expected 'owner/repo'.",
            file=sys.stderr,
        )
        sys.exit(1)
    return owner, repo_name


def _verify_approval(
    pr_number: int,
    repo: str,
    user_login: str,
    max_retries: int = 2,
    retry_delay: float = 5.0,
) -> tuple[dict | None, int]:
    """Verify the approval was registered by querying the reviews API.

    Fetches all reviews for the PR, filters to ``APPROVED`` reviews by
    *user_login* (case-insensitive), and returns the latest by
    ``submitted_at``.

    Args:
        pr_number: The pull request number.
        repo: ``owner/repo`` string.
        user_login: Expected approver login.
        max_retries: Number of additional verification attempts after
            the first failure (default 2, so 3 total attempts).
        retry_delay: Seconds to wait between retries.

    Returns:
        A tuple of ``(review_dict, retries_used)`` where *review_dict* is
        ``{"id": <int>, "submitted_at": <str>}`` if a matching review is
        found, or ``None`` after all attempts are exhausted.
        *retries_used* is the number of retry attempts performed
        (0 if matched on first attempt).
    """
    owner, repo_name = _validate_repo_format(repo)
    total_attempts = max_retries + 1

    for attempt in range(total_attempts):
        result = run_safe(
            [
                "gh",
                "api",
                f"repos/{owner}/{repo_name}/pulls/{pr_number}/reviews",
                "--paginate",
                "--jq",
                ".[]",
            ],
            capture_output=True,
            text=True,
            shell=False,
        )

        parse_errors = 0
        last_parse_error = ""
        reviews: list[dict] = []
        matching: list[dict] = []

        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if line:
                    try:
                        reviews.append(json.loads(line))
                    except (json.JSONDecodeError, TypeError) as exc:
                        parse_errors += 1
                        last_parse_error = str(exc)

            # Filter to APPROVED reviews by the current user (case-insensitive).
            # Guard against user: null from the API by coercing falsey values
            # to an empty dict before reading the login field.
            matching[:] = [
                r
                for r in reviews
                if (
                    isinstance(r, dict)
                    and (r.get("user") or {}).get("login", "").lower() == user_login.lower()
                    and r.get("state") == "APPROVED"
                )
            ]

            if matching:
                # Sort by submitted_at descending. Coerce non-string /
                # null values to "" so the sort key is always comparable.
                matching.sort(
                    key=lambda r: r.get("submitted_at") if isinstance(r.get("submitted_at"), str) else "",
                    reverse=True,
                )
                latest = matching[0]
                latest_id = latest.get("id")
                latest_submitted_at = latest.get("submitted_at")
                if isinstance(latest_id, int) and isinstance(latest_submitted_at, str):
                    return (
                        {"id": latest_id, "submitted_at": latest_submitted_at},
                        attempt,
                    )

        # Build a diagnostic reason for the failure.
        if result.returncode != 0:
            last_error = (result.stderr or result.stdout).strip()
            if not last_error:
                last_error = f"gh api exited with code {result.returncode}"
        elif not result.stdout.strip():
            last_error = "empty API response"
        elif parse_errors > 0 and not reviews:
            last_error = f"all {parse_errors} NDJSON line(s) failed JSON parsing (last error: {last_parse_error})"
        elif matching:
            last_error = (
                f"{len(matching)} matching APPROVED review(s) found but "
                f"with invalid fields (non-int id or non-str submitted_at)"
            )
        else:
            parts = ["no matching APPROVED review found"]
            if parse_errors > 0:
                parts.append(f"{parse_errors} NDJSON line(s) failed parsing")
            last_error = "; ".join(parts)

        # If not the last attempt, retry
        if attempt < total_attempts - 1:
            print(
                f"Verification attempt {attempt + 1}/{total_attempts} failed "
                f"({last_error}); retrying in {retry_delay}s...",
                file=sys.stderr,
            )
            time.sleep(retry_delay)

    return None, max_retries


def approve_pr(
    pr_number: int,
    repo: str,
    body: str | None = None,
) -> dict:
    """Approve a GitHub PR with verification and retry.

    Args:
        pr_number: The pull request number.
        repo: ``owner/repo`` string.
        body: Optional approval comment body. Defaults to
            :data:`_DEFAULT_APPROVAL_BODY`.

    Returns:
        Structured result dict with approval details.
    """
    if body is None:
        body = _DEFAULT_APPROVAL_BODY

    # Normalize repo once so both _submit_approval and _verify_approval
    # use the same cleaned value (strip whitespace, drop trailing .git,
    # validate owner/repo format).
    owner, repo_name = _validate_repo_format(repo)
    repo = f"{owner}/{repo_name}"

    _check_gh_available()
    user_login = _resolve_current_user()

    success, error_msg = _submit_approval(pr_number, repo, body)

    if not success:
        result = {
            "prNumber": pr_number,
            "repo": repo,
            "approved": False,
            "error": "approval_failed",
            "message": error_msg,
            "reviewId": None,
            "approver": user_login,
            "submittedAt": None,
            "verified": False,
            "retries": 0,
        }
        set_value("github.pr_approval_verified", False)
        set_value("github.pr_approval_review_id", None)
        return result

    review, retries_used = _verify_approval(pr_number, repo, user_login)

    if review is not None:
        result = {
            "prNumber": pr_number,
            "repo": repo,
            "approved": True,
            "reviewId": review["id"],
            "approver": user_login,
            "submittedAt": review["submitted_at"],
            "verified": True,
            "retries": retries_used,
        }
    else:
        result = {
            "prNumber": pr_number,
            "repo": repo,
            "approved": True,
            "reviewId": None,
            "approver": user_login,
            "submittedAt": None,
            "verified": False,
            "retries": retries_used,
        }

    set_value("github.pr_approval_verified", result["verified"])
    set_value("github.pr_approval_review_id", result["reviewId"])
    return result


def pr_approve_command() -> None:
    """CLI entry point for ``agdt-gh-pr-approve``."""
    parser = argparse.ArgumentParser(
        description="Approve a GitHub PR with verification and retry.",
    )
    parser.add_argument("--pr", type=int, default=None, help="PR number")
    parser.add_argument("--repo", type=str, default=None, help="GitHub repo (owner/repo)")
    parser.add_argument("--body", type=str, default=None, help="Approval comment body")
    args = parser.parse_args()

    # Resolve PR number
    pr_number = args.pr
    if pr_number is None:
        state_pr = get_value("github.pull_request_number")
        if state_pr is not None:
            try:
                pr_number = int(state_pr)
            except (ValueError, TypeError):
                print(
                    f"Error: github.pull_request_number in state must be an integer; "
                    f"got {state_pr!r}. Fix with: agdt-set github.pull_request_number 123",
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

    result = approve_pr(pr_number, repo, args.body)
    print(json.dumps(result, indent=2))
