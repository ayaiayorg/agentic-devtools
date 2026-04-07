"""
GitHub PR state query command.

Fetches structured PR state via the ``gh`` CLI, evaluates terminal
conditions, and writes ``github.*`` state keys for downstream commands.
"""

import argparse
import json
import sys
import time

from ...state import get_value, set_value
from ..subprocess_utils import run_safe
from .repo_resolution import resolve_github_repo

_GH_PR_JSON_FIELDS = [
    "state",
    "mergedAt",
    "mergeable",
    "mergeStateStatus",
    "headRefOid",
    "isDraft",
    "locked",
]

_GH_PR_JSON_FIELDS_NO_LOCKED = [f for f in _GH_PR_JSON_FIELDS if f != "locked"]


def _evaluate_terminal_condition(
    state: str,
    merged_at: str | None,
    locked: bool | None,
) -> tuple[bool, str | None]:
    """Return ``(is_terminal, reason)`` for the given PR state."""
    if state == "MERGED":
        return True, "PR is merged"
    if state == "CLOSED":
        return True, "PR is closed (not merged)"
    if locked is True:
        return True, "PR is locked"
    return False, None


def _fetch_pr_with_retry(
    pr_number: int,
    repo: str,
    *,
    max_retries: int = 2,
    retry_delay: float = 10.0,
) -> dict:
    """Fetch PR data from ``gh pr view``, with retry and locked-field fallback.

    Returns the parsed JSON dict on success.
    Calls ``sys.exit(1)`` after all retries are exhausted.
    """
    fields = list(_GH_PR_JSON_FIELDS)
    last_error = ""

    for attempt in range(1 + max_retries):
        cmd = [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--repo",
            repo,
            "--json",
            ",".join(fields),
        ]
        try:
            result = run_safe(cmd, capture_output=True, text=True, shell=False)
        except FileNotFoundError:
            last_error = "Error: 'gh' CLI is not installed or not on PATH. Install from https://cli.github.com/"
            if attempt < max_retries:
                print(
                    f"Retry {attempt + 1}/{max_retries}: {last_error}",
                    file=sys.stderr,
                )
                time.sleep(retry_delay)
                continue
            print(last_error, file=sys.stderr)
            sys.exit(1)

        if result.returncode != 0:
            stderr_text = (result.stderr or "").strip()
            # Handle unknown field "locked" by retrying without it
            if "locked" in fields and (
                "unknown field" in stderr_text.lower() or "invalid field" in stderr_text.lower()
            ):
                fields = list(_GH_PR_JSON_FIELDS_NO_LOCKED)
                # Don't count this as a retry — redo immediately with new fields
                continue

            last_error = stderr_text or f"gh pr view exited with code {result.returncode}"
            if attempt < max_retries:
                print(
                    f"Retry {attempt + 1}/{max_retries}: {last_error}",
                    file=sys.stderr,
                )
                time.sleep(retry_delay)
                continue

            print(
                f"Error: Failed to fetch PR #{pr_number} from {repo} after {max_retries + 1} attempts: {last_error}",
                file=sys.stderr,
            )
            sys.exit(1)

        # Parse JSON
        try:
            data = json.loads(result.stdout)
        except (json.JSONDecodeError, TypeError) as exc:
            last_error = f"Malformed JSON from gh: {exc}"
            if attempt < max_retries:
                print(
                    f"Retry {attempt + 1}/{max_retries}: {last_error}",
                    file=sys.stderr,
                )
                time.sleep(retry_delay)
                continue

            print(
                f"Error: Failed to parse gh output for PR #{pr_number}: {last_error}\nRaw output: {result.stdout!r}",
                file=sys.stderr,
            )
            sys.exit(1)

        # If we retried without locked, mark it as None in the response
        if "locked" not in fields:
            data.setdefault("locked", None)

        return data

    # Should not reach here, but guard defensively
    print(f"Error: Exhausted retries for PR #{pr_number}", file=sys.stderr)
    sys.exit(1)


def get_pr_state(pr_number: int, repo: str) -> dict:
    """Fetch PR state, evaluate terminal conditions, and write state keys.

    Returns a structured dict with all output fields.
    """
    data = _fetch_pr_with_retry(pr_number, repo)

    pr_state = data.get("state", "")
    head_ref_oid = data.get("headRefOid") or ""
    head_ref_oid_short = head_ref_oid[:7] if head_ref_oid else ""
    mergeable = data.get("mergeable")
    merge_state_status = data.get("mergeStateStatus")
    merged_at = data.get("mergedAt")
    is_draft = data.get("isDraft", False)
    locked = data.get("locked")

    is_terminal, terminal_reason = _evaluate_terminal_condition(
        pr_state,
        merged_at,
        locked,
    )

    result = {
        "prNumber": pr_number,
        "repo": repo,
        "state": pr_state,
        "headRefOid": head_ref_oid,
        "headRefOidShort": head_ref_oid_short,
        "mergeable": mergeable,
        "mergeStateStatus": merge_state_status,
        "mergedAt": merged_at,
        "isDraft": is_draft,
        "locked": locked,
        "isTerminal": is_terminal,
        "terminalReason": terminal_reason,
    }

    # Write state keys for downstream commands
    set_value("github.pull_request_number", pr_number)
    set_value("github.repo", repo)
    set_value("github.pr_state", pr_state)
    set_value("github.head_ref_oid", head_ref_oid)
    set_value("github.head_ref_oid_short", head_ref_oid_short)
    set_value("github.mergeable", mergeable)
    set_value("github.merge_state_status", merge_state_status)
    set_value("github.is_draft", is_draft)
    set_value("github.is_terminal", is_terminal)

    return result


def pr_state_command() -> None:
    """CLI entry point for ``agdt-gh-pr-state``."""
    parser = argparse.ArgumentParser(
        prog="agdt-gh-pr-state",
        description="Fetch structured GitHub PR state.",
    )
    parser.add_argument("--pr", type=int, default=None, help="PR number")
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="owner/repo (auto-detected if omitted)",
    )
    args = parser.parse_args()

    # Resolve PR number
    pr_number = args.pr
    if pr_number is None:
        pr_number = get_value("github.pull_request_number")
        if pr_number is not None:
            pr_number = int(pr_number)
    if pr_number is None:
        print(
            "Error: PR number required. Provide --pr or set github.pull_request_number in state.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Resolve repo
    repo = resolve_github_repo(args.repo)

    result = get_pr_state(pr_number, repo)
    print(json.dumps(result, indent=2))
