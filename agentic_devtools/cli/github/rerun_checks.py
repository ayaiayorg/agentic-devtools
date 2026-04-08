"""Re-run failed/stale workflow runs for a PR's head commit.

Provides ``agdt-gh-rerun-checks`` — a synchronous CLI command that:

1. Fetches workflow runs for a given commit SHA via the GitHub Actions API.
2. Filters to failed and stale (and optionally cancelled) runs.
3. Optionally filters by workflow name pattern.
4. Re-runs each eligible workflow via the GitHub Actions API.
5. Prints structured JSON to stdout and writes state keys.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from ...state import get_value, set_value
from ..subprocess_utils import run_safe
from .repo_resolution import _validate_repo_format, resolve_github_repo

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RERUNNABLE_CONCLUSIONS = frozenset(["failure", "stale"])
_RERUNNABLE_CONCLUSIONS_WITH_CANCELLED = frozenset(["failure", "cancelled", "stale"])
_MAX_RETRIES = 2
_RETRY_DELAY_SECONDS = 10.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fetch_workflow_runs(repo: str, head_sha: str) -> list[dict]:
    """Fetch all workflow runs for *head_sha* via ``gh api``.

    Retries up to ``_MAX_RETRIES`` times on failure.  Calls ``sys.exit(1)``
    if all attempts fail.
    """
    owner, repo_name = repo.split("/", 1)
    args = [
        "gh",
        "api",
        f"repos/{owner}/{repo_name}/actions/runs?head_sha={head_sha}&per_page=100",
        "--paginate",
        "--jq",
        ".workflow_runs[]",
    ]

    last_error: str = ""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            result = run_safe(args, capture_output=True, text=True, shell=False)
        except FileNotFoundError:
            print(
                "Error: 'gh' CLI is not installed or not on PATH. Install from https://cli.github.com/",
                file=sys.stderr,
            )
            sys.exit(1)
        except OSError as exc:
            print(
                f"Error: Failed to execute 'gh' CLI: {exc}",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            if result.returncode != 0:
                last_error = result.stderr.strip() or "Unknown error"
                if attempt < _MAX_RETRIES:
                    print(
                        f"Warning: gh api failed (attempt {attempt + 1}): {last_error}",
                        file=sys.stderr,
                    )
                    time.sleep(_RETRY_DELAY_SECONDS)
                    continue
                break

            stdout = result.stdout.strip()
            if not stdout:
                return []

            runs = [json.loads(line) for line in stdout.splitlines() if line.strip()]
            return runs

        except json.JSONDecodeError as exc:
            last_error = f"JSON parse error: {exc}"
            if attempt < _MAX_RETRIES:
                print(
                    f"Warning: JSON parse error (attempt {attempt + 1}): {exc}",
                    file=sys.stderr,
                )
                time.sleep(_RETRY_DELAY_SECONDS)
                continue
            break

    print(
        f"Error: Failed to fetch workflow runs after {_MAX_RETRIES + 1} attempts: {last_error}",
        file=sys.stderr,
    )
    sys.exit(1)


def _filter_failed_runs(
    runs: list[dict],
    name_filter: str | None = None,
    include_cancelled: bool = True,
) -> tuple[list[dict], list[dict]]:
    """Partition *runs* into ``(eligible, skipped)``.

    A run is eligible when its ``conclusion`` is ``"failure"`` (or
    ``"cancelled"`` when *include_cancelled* is ``True``) **and** it
    matches the optional *name_filter* (case-insensitive substring).

    Runs excluded solely by the name filter are returned in *skipped*
    as their original run dictionaries, unmodified. Any reporting-only
    metadata such as ``reason: "excluded-by-filter"`` is added later by
    the caller.
    """
    conclusions = _RERUNNABLE_CONCLUSIONS_WITH_CANCELLED if include_cancelled else _RERUNNABLE_CONCLUSIONS

    eligible: list[dict] = []
    skipped: list[dict] = []

    for run in runs:
        conclusion = run.get("conclusion") or ""
        if conclusion not in conclusions:
            continue  # not a rerunnable conclusion (failure/stale, plus cancelled when enabled)

        if name_filter and name_filter.lower() not in (run.get("name") or "").lower():
            skipped.append(run)
            continue

        eligible.append(run)

    return eligible, skipped


def _rerun_single_workflow(repo: str, run_id: int) -> tuple[bool, str]:
    """Trigger a re-run for a single workflow run.

    Returns ``(True, "triggered")`` on success, ``(False, error_message)``
    on failure.  Does **not** retry — re-run failures are often permanent.
    """
    owner, repo_name = repo.split("/", 1)
    args = [
        "gh",
        "api",
        "-X",
        "POST",
        f"repos/{owner}/{repo_name}/actions/runs/{run_id}/rerun",
    ]

    try:
        result = run_safe(args, capture_output=True, text=True, shell=False)
    except FileNotFoundError:
        return False, "GitHub CLI 'gh' was not found. Please install 'gh' and ensure it is available on PATH."
    except OSError as exc:
        return False, f"Failed to execute GitHub CLI 'gh': {exc}"
    if result.returncode == 0:
        return True, "triggered"
    return False, result.stderr.strip() or "Unknown error"


# ---------------------------------------------------------------------------
# Public orchestration function
# ---------------------------------------------------------------------------


def rerun_failed_checks(
    pr_number: int,
    repo: str,
    head_sha: str,
    name_filter: str | None = None,
    include_cancelled: bool = True,
) -> dict:
    """Orchestrate re-running failed workflow runs for a PR.

    Returns a structured dict summarising what was re-run.
    """
    validated = _validate_repo_format(repo)
    if not validated:
        print(
            f"Error: Invalid repo format: {repo!r}. Expected 'owner/repo'.",
            file=sys.stderr,
        )
        sys.exit(1)
    repo = validated

    runs = _fetch_workflow_runs(repo, head_sha)
    eligible, skipped = _filter_failed_runs(runs, name_filter, include_cancelled)

    rerun_workflows: list[dict] = []
    failed_to_rerun: list[dict] = []

    for run in eligible:
        success, message = _rerun_single_workflow(repo, run["id"])
        info: dict = {
            "runId": run["id"],
            "name": run.get("name", "unknown"),
            "event": run.get("event", "unknown"),
            "conclusion": run.get("conclusion", "unknown"),
        }
        if success:
            info["rerunStatus"] = "triggered"
            rerun_workflows.append(info)
        else:
            info["rerunStatus"] = "failed"
            info["error"] = message
            failed_to_rerun.append(info)

    skipped_workflows = [
        {
            "runId": r["id"],
            "name": r.get("name", "unknown"),
            "event": r.get("event", "unknown"),
            "conclusion": r.get("conclusion", "unknown"),
            "reason": "excluded-by-filter",
        }
        for r in skipped
    ]

    output = {
        "prNumber": pr_number,
        "repo": repo,
        "headRefOid": head_sha,
        "rerunCount": len(rerun_workflows),
        "skippedCount": len(skipped_workflows),
        "failedToRerunCount": len(failed_to_rerun),
        "rerunWorkflows": rerun_workflows,
        "skippedWorkflows": skipped_workflows,
        "failedToRerun": failed_to_rerun,
        "filter": name_filter,
    }

    set_value("github.rerun_checks_count", len(rerun_workflows))
    set_value("github.rerun_checks_failed_to_rerun", len(failed_to_rerun))

    return output


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def rerun_checks_command() -> None:
    """CLI entry point for ``agdt-gh-rerun-checks``."""
    parser = argparse.ArgumentParser(
        description="Re-run failed/stale CI workflow runs for a PR.",
    )
    parser.add_argument("--pr", type=int, default=None, help="Pull request number")
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="GitHub repository in owner/repo format",
    )
    parser.add_argument(
        "--head-sha",
        type=str,
        default=None,
        help="Head commit SHA (overrides state)",
    )
    parser.add_argument(
        "--filter",
        type=str,
        default=None,
        dest="name_filter",
        help="Only re-run workflows whose name contains this string (case-insensitive)",
    )
    parser.add_argument(
        "--include-cancelled",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include cancelled runs alongside failed/stale runs (default: True)",
    )

    args = parser.parse_args()

    # Resolve PR number
    pr_number = args.pr
    if pr_number is None:
        state_val = get_value("github.pull_request_number")
        if state_val is not None:
            try:
                pr_number = int(state_val)
            except (ValueError, TypeError):
                print(
                    "Error: github.pull_request_number in state must be a numeric PR number.",
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

    # Resolve head SHA
    head_sha = args.head_sha
    if head_sha is None:
        head_sha = get_value("github.head_ref_oid")
        if isinstance(head_sha, str):
            head_sha = head_sha.strip() or None
        else:
            head_sha = None
    if head_sha is None:
        print(
            "Error: head_sha is required. Run agdt-gh-pr-state first, or provide --head-sha.",
            file=sys.stderr,
        )
        sys.exit(1)

    result = rerun_failed_checks(
        pr_number,
        repo,
        head_sha,
        name_filter=args.name_filter,
        include_cancelled=args.include_cancelled,
    )

    print(json.dumps(result, indent=2))
