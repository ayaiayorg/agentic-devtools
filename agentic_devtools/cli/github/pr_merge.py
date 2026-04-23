"""
Merge a GitHub PR with verification and retry.

Executes ``gh pr merge`` with a configurable strategy, verifies the merge
by re-fetching PR state, and retries once if the PR is still OPEN after
the initial merge command.

Returns structured JSON to stdout and writes ``github.*`` state keys for
downstream commands.
"""

import argparse
import json
import shutil
import sys
import time

from ...state import get_value, set_value
from ..subprocess_utils import run_safe
from .repo_resolution import resolve_github_repo

_DEFAULT_STRATEGY = "rebase"
_VALID_STRATEGIES = ("squash", "merge", "rebase")


def _check_gh_available() -> None:
    """Verify ``gh`` CLI is installed, or exit with a helpful error."""
    if shutil.which("gh") is None:
        print(
            "Error: 'gh' CLI is not installed or not on PATH. Install from https://cli.github.com/",
            file=sys.stderr,
        )
        sys.exit(1)


def _classify_merge_error(stderr: str) -> str:
    """Classify a merge error from ``gh pr merge`` stderr content.

    Args:
        stderr: The stderr output from the failed merge command.

    Returns:
        A string error classification.
    """
    lower = stderr.lower()
    if "conflict" in lower:
        return "merge_conflict"
    if any(phrase in lower for phrase in ("protected branch", "required status", "branch protection")):
        return "branch_protection"
    if "not mergeable" in lower or "not in a mergeable state" in lower:
        return "not_mergeable"
    return "merge_failed"


def _execute_merge(
    pr_number: int,
    repo: str,
    strategy: str,
    delete_branch: bool,
) -> tuple[bool, str]:
    """Execute ``gh pr merge`` and return success status.

    Args:
        pr_number: The pull request number.
        repo: ``owner/repo`` string.
        strategy: Merge strategy (``squash``, ``merge``, or ``rebase``).
        delete_branch: Whether to pass ``--delete-branch``.

    Returns:
        ``(True, "")`` on exit code 0,
        ``(False, stderr_content)`` on non-zero exit.
    """
    cmd = ["gh", "pr", "merge", str(pr_number), "--repo", repo, f"--{strategy}"]
    if delete_branch:
        cmd.append("--delete-branch")

    try:
        result = run_safe(cmd, capture_output=True, text=True, shell=False)
    except (FileNotFoundError, OSError) as exc:
        return (False, f"Failed to execute 'gh' CLI: {exc}")
    if result.returncode == 0:
        return (True, "")
    error_content = (result.stderr or result.stdout or "Merge command failed with no output.").strip()
    return (False, error_content)


def _verify_merge(pr_number: int, repo: str) -> dict:
    """Verify merge by fetching PR state via ``gh pr view``.

    Args:
        pr_number: The pull request number.
        repo: ``owner/repo`` string.

    Returns:
        A dict with ``state`` and ``mergedAt`` keys.  Returns
        ``{"state": "UNKNOWN", "mergedAt": None}`` on any failure.
    """
    cmd = [
        "gh",
        "pr",
        "view",
        str(pr_number),
        "--repo",
        repo,
        "--json",
        "state,mergedAt",
    ]
    try:
        result = run_safe(cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            return {"state": "UNKNOWN", "mergedAt": None}
        return json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError, ValueError, FileNotFoundError, OSError):
        return {"state": "UNKNOWN", "mergedAt": None}


def merge_pr(
    pr_number: int,
    repo: str,
    strategy: str = _DEFAULT_STRATEGY,
    delete_branch: bool = True,
) -> dict:
    """Merge a GitHub PR with verification and retry.

    Args:
        pr_number: The pull request number.
        repo: ``owner/repo`` string.
        strategy: Merge strategy (``squash``, ``merge``, or ``rebase``).
        delete_branch: Whether to delete the source branch after merge.

    Returns:
        Structured result dict with merge details.
    """
    _check_gh_available()

    success, error_msg = _execute_merge(pr_number, repo, strategy, delete_branch)

    if not success:
        error_type = _classify_merge_error(error_msg)
        result: dict = {
            "prNumber": pr_number,
            "repo": repo,
            "merged": False,
            "state": "UNKNOWN",
            "mergedAt": None,
            "strategy": strategy,
            "deleteBranch": delete_branch,
            "error": error_type,
            "message": error_msg,
            "retries": 0,
        }
        set_value("github.pr_merged", False)
        set_value("github.pr_merged_at", None)
        set_value("github.pr_merge_strategy", strategy)
        return result

    # Verify merge succeeded
    verification = _verify_merge(pr_number, repo)

    if verification.get("state", "UNKNOWN") == "MERGED" and verification.get("mergedAt"):
        result = {
            "prNumber": pr_number,
            "repo": repo,
            "merged": True,
            "state": "MERGED",
            "mergedAt": verification["mergedAt"],
            "strategy": strategy,
            "deleteBranch": delete_branch,
            "retries": 0,
        }
        set_value("github.pr_merged", True)
        set_value("github.pr_merged_at", verification["mergedAt"])
        set_value("github.pr_merge_strategy", strategy)
        return result

    if verification.get("state", "UNKNOWN") == "OPEN":
        print(
            "Merge verification: PR still OPEN — retrying in 5s...",
            file=sys.stderr,
        )
        time.sleep(5.0)

        retry_success, retry_error = _execute_merge(pr_number, repo, strategy, delete_branch)
        if not retry_success:
            error_type = _classify_merge_error(retry_error)
            result = {
                "prNumber": pr_number,
                "repo": repo,
                "merged": False,
                "state": "OPEN",
                "mergedAt": None,
                "strategy": strategy,
                "deleteBranch": delete_branch,
                "error": error_type,
                "message": retry_error,
                "retries": 1,
            }
            set_value("github.pr_merged", False)
            set_value("github.pr_merged_at", None)
            set_value("github.pr_merge_strategy", strategy)
            return result

        re_verification = _verify_merge(pr_number, repo)
        if re_verification.get("state", "UNKNOWN") == "MERGED" and re_verification.get("mergedAt"):
            result = {
                "prNumber": pr_number,
                "repo": repo,
                "merged": True,
                "state": "MERGED",
                "mergedAt": re_verification["mergedAt"],
                "strategy": strategy,
                "deleteBranch": delete_branch,
                "retries": 1,
            }
            set_value("github.pr_merged", True)
            set_value("github.pr_merged_at", re_verification["mergedAt"])
            set_value("github.pr_merge_strategy", strategy)
            return result

        result = {
            "prNumber": pr_number,
            "repo": repo,
            "merged": False,
            "state": re_verification.get("state", "OPEN"),
            "mergedAt": None,
            "strategy": strategy,
            "deleteBranch": delete_branch,
            "error": "merge_verification_failed",
            "message": "PR is still OPEN after merge command and 1 retry.",
            "retries": 1,
        }
        set_value("github.pr_merged", False)
        set_value("github.pr_merged_at", None)
        set_value("github.pr_merge_strategy", strategy)
        return result

    if verification.get("state", "UNKNOWN") == "CLOSED" and not verification.get("mergedAt"):
        result = {
            "prNumber": pr_number,
            "repo": repo,
            "merged": False,
            "state": "CLOSED",
            "mergedAt": None,
            "strategy": strategy,
            "deleteBranch": delete_branch,
            "error": "closed_not_merged",
            "message": "PR was closed but not merged.",
            "retries": 0,
        }
        set_value("github.pr_merged", False)
        set_value("github.pr_merged_at", None)
        set_value("github.pr_merge_strategy", strategy)
        return result

    # Unexpected state (including UNKNOWN)
    result = {
        "prNumber": pr_number,
        "repo": repo,
        "merged": False,
        "state": verification.get("state", "UNKNOWN"),
        "mergedAt": None,
        "strategy": strategy,
        "deleteBranch": delete_branch,
        "error": "verification_error",
        "message": f"Unexpected PR state after merge: {verification.get('state', 'UNKNOWN')}",
        "retries": 0,
    }
    set_value("github.pr_merged", False)
    set_value("github.pr_merged_at", None)
    set_value("github.pr_merge_strategy", strategy)
    return result


def pr_merge_command() -> None:
    """CLI entry point for ``agdt-gh-pr-merge``."""
    parser = argparse.ArgumentParser(
        description="Merge a GitHub PR with verification and retry.",
    )
    parser.add_argument("--pr", type=int, default=None, help="PR number")
    parser.add_argument("--repo", type=str, default=None, help="GitHub repo (owner/repo)")
    parser.add_argument(
        "--strategy",
        type=str,
        default=_DEFAULT_STRATEGY,
        choices=list(_VALID_STRATEGIES),
        help="Merge strategy (default: rebase)",
    )
    parser.add_argument(
        "--no-delete-branch",
        action="store_true",
        default=False,
        help="Do not delete the source branch after merge",
    )
    args = parser.parse_args()

    delete_branch = not args.no_delete_branch

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

    result = merge_pr(pr_number, repo, args.strategy, delete_branch)
    print(json.dumps(result, indent=2))
