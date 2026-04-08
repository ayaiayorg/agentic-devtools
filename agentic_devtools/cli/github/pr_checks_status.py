"""
PR CI/status check verification via dual-source: ``gh pr checks`` + check-suites API.

Provides ``get_pr_checks_status()`` for programmatic use and
``pr_checks_status_command()`` as the CLI entry point for
``agdt-gh-pr-checks-status``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from ...state import get_value, set_value
from ..subprocess_utils import run_safe
from .repo_resolution import resolve_github_repo

_GH_PR_CHECKS_JSON_FIELDS = "name,state,bucket,workflow,completedAt,description"
_CHECK_SUITE_GREEN_CONCLUSIONS = frozenset(["success", "neutral", "skipped"])
_MAX_RETRIES = 2
_RETRY_DELAY_SECONDS = 10.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fetch_pr_checks(pr_number: int, repo: str) -> list[dict]:
    """Fetch structured check results via ``gh pr checks --json``.

    Retries up to *_MAX_RETRIES* times on failure.  Calls ``sys.exit(1)``
    when all retries are exhausted.
    """
    cmd = [
        "gh",
        "pr",
        "checks",
        str(pr_number),
        "--repo",
        repo,
        "--json",
        _GH_PR_CHECKS_JSON_FIELDS,
    ]

    last_error = ""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            result = run_safe(cmd, capture_output=True, text=True, shell=False)
        except FileNotFoundError:
            print(
                "Error: 'gh' CLI is not installed or not on PATH. "
                "Install from https://cli.github.com/",
                file=sys.stderr,
            )
            sys.exit(1)
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                if isinstance(data, list):
                    return data
                last_error = f"Unexpected JSON type: {type(data).__name__}"
            except json.JSONDecodeError as exc:
                last_error = f"JSON parse error: {exc}"
        else:
            last_error = (result.stderr or "").strip() or f"exit code {result.returncode}"

        if attempt < _MAX_RETRIES:
            print(
                f"Warning: gh pr checks failed (attempt {attempt + 1}/{_MAX_RETRIES + 1}): "
                f"{last_error}. Retrying in {_RETRY_DELAY_SECONDS}s …",
                file=sys.stderr,
            )
            time.sleep(_RETRY_DELAY_SECONDS)

    print(
        f"Error: gh pr checks failed after {_MAX_RETRIES + 1} attempts: {last_error}",
        file=sys.stderr,
    )
    sys.exit(1)


def _classify_checks(checks: list[dict]) -> dict:
    """Classify checks by their ``bucket`` field.

    Returns a dict with counts and lists of failed/pending check names.
    """
    passed = 0
    failed = 0
    pending = 0
    skipped = 0
    cancelled = 0
    failed_checks: list[str] = []
    pending_checks: list[str] = []

    for check in checks:
        bucket = check.get("bucket", "")
        name = check.get("name", "unknown")
        if bucket == "pass":
            passed += 1
        elif bucket == "fail":
            failed += 1
            failed_checks.append(name)
        elif bucket == "pending":
            pending += 1
            pending_checks.append(name)
        elif bucket == "skipping":
            skipped += 1
        elif bucket == "cancel":
            cancelled += 1
        # Unknown bucket values are silently ignored (not counted)

    return {
        "passed": passed,
        "failed": failed,
        "pending": pending,
        "skipped": skipped,
        "cancelled": cancelled,
        "total": len(checks),
        "failedChecks": failed_checks,
        "pendingChecks": pending_checks,
    }


def _normalize_repo(repo: str) -> str:
    """Validate and normalize a *owner/repo* string.

    Strips whitespace and a trailing ``.git`` suffix, then verifies the
    value contains exactly one ``/`` separator.  Calls ``sys.exit(1)``
    with a user-facing message when the format is invalid.
    """
    repo = repo.strip()
    if repo.endswith(".git"):
        repo = repo[: -len(".git")]
    if "/" not in repo or repo.count("/") != 1:
        print(
            f"Error: invalid repo format '{repo}'. Expected 'owner/repo' "
            "(for example: agdt-set github.repo myorg/myrepo).",
            file=sys.stderr,
        )
        sys.exit(1)
    owner, name = repo.split("/", 1)
    if not owner or not name:
        print(
            f"Error: invalid repo format '{repo}'. Both owner and repo name "
            "must be non-empty (for example: agdt-set github.repo myorg/myrepo).",
            file=sys.stderr,
        )
        sys.exit(1)
    return repo


def _fetch_check_suites(repo: str, head_sha: str) -> list[dict]:
    """Fetch check-suite data via ``gh api`` with pagination.

    Returns an empty list on persistent failure (graceful degradation).
    """
    owner, repo_name = repo.split("/", 1)
    cmd = [
        "gh",
        "api",
        f"repos/{owner}/{repo_name}/commits/{head_sha}/check-suites?per_page=100",
        "--paginate",
        "--jq",
        ".check_suites[]",
    ]

    last_error = ""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            result = run_safe(cmd, capture_output=True, text=True, shell=False)
        except FileNotFoundError:
            print(
                "Warning: 'gh' CLI is not installed or not on PATH. "
                "Skipping check-suite verification. "
                "Install from https://cli.github.com/",
                file=sys.stderr,
            )
            return []
        if result.returncode == 0:
            stdout = result.stdout.strip()
            if not stdout:
                return []
            try:
                suites = [json.loads(line) for line in stdout.splitlines() if line.strip()]
                return suites
            except json.JSONDecodeError as exc:
                last_error = f"JSON parse error: {exc}"
        else:
            last_error = (result.stderr or "").strip() or f"exit code {result.returncode}"

        if attempt < _MAX_RETRIES:
            print(
                f"Warning: check-suites API failed (attempt {attempt + 1}/{_MAX_RETRIES + 1}): "
                f"{last_error}. Retrying in {_RETRY_DELAY_SECONDS}s …",
                file=sys.stderr,
            )
            time.sleep(_RETRY_DELAY_SECONDS)

    print(
        f"Warning: check-suites API failed after {_MAX_RETRIES + 1} attempts: {last_error}. "
        "Skipping check-suite verification.",
        file=sys.stderr,
    )
    return []


def _verify_check_suites(suites: list[dict]) -> tuple[bool, list[dict]]:
    """Verify that all check suites are green.

    Returns ``(all_verified, discrepancies)`` where each discrepancy is a
    dict with ``suiteId``, ``app``, ``status``, and ``conclusion``.
    """
    discrepancies: list[dict] = []
    for suite in suites:
        status = suite.get("status", "")
        conclusion = suite.get("conclusion") or ""
        app_raw = suite.get("app")
        if isinstance(app_raw, dict):
            app_slug = app_raw.get("slug", "unknown")
        else:
            app_slug = str(app_raw) if app_raw else "unknown"

        if status != "completed" or conclusion not in _CHECK_SUITE_GREEN_CONCLUSIONS:
            discrepancies.append(
                {
                    "suiteId": suite.get("id"),
                    "app": app_slug,
                    "status": status,
                    "conclusion": conclusion,
                }
            )
    return (len(discrepancies) == 0, discrepancies)


def _reconcile_results(
    classification: dict,
    suites_verified: bool,
    discrepancies: list[dict],
    head_sha_available: bool,
) -> dict:
    """Determine final status and build output dict."""
    # Base status from classification
    if classification["pending"] > 0:
        status = "pending"
    elif classification["failed"] > 0:
        status = "failed"
    elif classification["cancelled"] > 0:
        status = "cancelled"
    else:
        status = "all-pass"

    check_suites_verified = False

    if head_sha_available:
        if status == "all-pass" and not suites_verified:
            # Override based on discrepancies
            for d in discrepancies:
                if d.get("status") != "completed":
                    status = "pending"
                    break
                # Any completed suite with a non-green conclusion
                # (cancelled, timed_out, action_required, etc.) is a failure.
                if d.get("conclusion") not in _CHECK_SUITE_GREEN_CONCLUSIONS:
                    status = "failed"
                    break
        check_suites_verified = suites_verified
    # else: head_sha not available → checkSuitesVerified stays False

    return {
        "status": status,
        "totalChecks": classification["total"],
        "passed": classification["passed"],
        "failed": classification["failed"],
        "pending": classification["pending"],
        "skipped": classification["skipped"],
        "cancelled": classification["cancelled"],
        "failedChecks": classification["failedChecks"],
        "pendingChecks": classification["pendingChecks"],
        "checkSuitesVerified": check_suites_verified,
        "checkSuiteDiscrepancies": discrepancies if head_sha_available else [],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_pr_checks_status(
    pr_number: int,
    repo: str,
    head_sha: str | None = None,
) -> dict:
    """Fetch, classify, verify, and reconcile PR check status.

    Writes ``github.pr_checks_status``, ``github.pr_checks_failed``, and
    ``github.pr_checks_pending`` to state.

    Returns the full structured result dict.
    """
    repo = _normalize_repo(repo)
    checks = _fetch_pr_checks(pr_number, repo)
    classification = _classify_checks(checks)

    if head_sha is not None:
        suites = _fetch_check_suites(repo, head_sha)
        if suites:
            suites_verified, discrepancies = _verify_check_suites(suites)
        else:
            suites_verified = False
            discrepancies = []
        head_sha_available = True
    else:
        suites_verified = False
        discrepancies = []
        head_sha_available = False

    result = _reconcile_results(classification, suites_verified, discrepancies, head_sha_available)
    result["prNumber"] = pr_number
    result["repo"] = repo

    # Persist to state for downstream commands
    set_value("github.pr_checks_status", result["status"])
    set_value("github.pr_checks_failed", result["failedChecks"])
    set_value("github.pr_checks_pending", result["pendingChecks"])

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def pr_checks_status_command() -> None:
    """CLI entry point for ``agdt-gh-pr-checks-status``."""
    parser = argparse.ArgumentParser(
        description="Check CI/status check results for a GitHub PR.",
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
        help="Head commit SHA for check-suite verification",
    )
    args = parser.parse_args()

    # Resolve PR number
    pr_number = args.pr
    if pr_number is None:
        pr_number = get_value("github.pull_request_number")
    if pr_number is None:
        print(
            "Error: PR number required. Provide --pr or set github.pull_request_number in state (via agdt-set).",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        pr_number = int(pr_number)
    except (TypeError, ValueError):
        print(
            "Error: PR number must be an integer. Provide --pr <number> or set "
            "github.pull_request_number to a valid integer (for example: "
            "agdt-set github.pull_request_number 123).",
            file=sys.stderr,
        )
        sys.exit(1)

    # Resolve repo
    repo = resolve_github_repo(args.repo)

    # Resolve head SHA (optional — graceful degradation)
    head_sha = args.head_sha
    if head_sha is None:
        head_sha = get_value("github.head_ref_oid")
        if head_sha is not None:
            head_sha = str(head_sha)
    if head_sha is None:
        print(
            "Notice: head_ref_oid not available — skipping check-suite verification. "
            "Provide --head-sha or set github.head_ref_oid in state for dual verification.",
            file=sys.stderr,
        )

    result = get_pr_checks_status(pr_number, repo, head_sha)
    print(json.dumps(result, indent=2))
