"""Automated polling loop for PR merge-readiness.

Calls sibling Python functions (``get_pr_state``, ``get_copilot_review_status``,
``get_pr_checks_status``, ``rerun_failed_checks``) each iteration until the PR
is ready to merge, a terminal/blocking state is reached, or max wait is exceeded.

Public API
----------
- :func:`poll_pr_ready` — core polling function (blocking).
- :func:`pr_poll_ready_command` — CLI entry point.
- :func:`_evaluate_iteration` — single iteration evaluation.
- :func:`_should_rerun_checks` — re-run eligibility check.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from ...state import get_value, set_value
from .copilot_review_status import get_copilot_review_status
from .pr_checks_status import get_pr_checks_status
from .pr_state import get_pr_state
from .repo_resolution import resolve_github_repo
from .rerun_checks import rerun_failed_checks

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_POLL_INTERVAL = 60
_DEFAULT_MAX_WAIT = 600
_MIN_POLL_INTERVAL = 10
_MAX_POLL_INTERVAL = 300
_MIN_MAX_WAIT = 30
_MAX_MAX_WAIT = 3600
_MAX_CONSECUTIVE_ERRORS = 3

# Terminal reason mapping from get_pr_state terminalReason strings
_TERMINAL_REASON_MAP: dict[str, str] = {
    "PR is merged": "pr_merged",
    "PR is closed (not merged)": "pr_closed",
    "PR is locked": "pr_locked",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _should_rerun_checks(
    rerun_stale: bool,
    ci_status: str,
    last_rerun_time: float | None,
    poll_interval: int,
) -> bool:
    """Return ``True`` if stale/failed checks should be re-run.

    Re-runs are allowed when:
    - *rerun_stale* is enabled
    - *ci_status* indicates failure or cancellation
    - Cooldown period (one *poll_interval*) has elapsed since last re-run
    """
    if not rerun_stale:
        return False
    if ci_status not in ("cancelled", "failed"):
        return False
    if last_rerun_time is not None and (time.time() - last_rerun_time) < poll_interval:
        return False
    return True


def _evaluate_iteration(
    pr_number: int,
    repo: str,
    rerun_stale: bool,
    last_rerun_time: float | None,
    poll_interval: int,
) -> tuple[dict | None, str | None, float | None]:
    """Execute one iteration of the polling loop.

    Returns ``(result_or_None, head_sha, updated_last_rerun_time)``.

    - If a terminal/actionable state is detected, *result* is a dict with
      ``ready``, ``reason``, ``actionRequired`` and associated fields.
    - If polling should continue, *result* is ``None``.
    """
    # 1. Fetch PR state
    pr_state = get_pr_state(pr_number, repo)
    head_sha = pr_state.get("headRefOid")
    head_sha_short_raw = pr_state.get("headRefOidShort", "")
    head_sha_short = head_sha_short_raw if isinstance(head_sha_short_raw, str) else ""

    # Validate head SHA — downstream calls need a non-empty commit hash
    if not isinstance(head_sha, str) or not head_sha.strip():
        result = {
            "headRefOid": head_sha if isinstance(head_sha, str) else "",
            "headRefOidShort": head_sha_short,
            "ready": False,
            "reason": "api_error",
            "copilotReviewStatus": None,
            "copilotReviewId": None,
            "copilotReviewUrl": None,
            "ciStatus": None,
            "actionRequired": "investigate-api-error",
        }
        return result, None, last_rerun_time

    head_sha = head_sha.strip()

    base_fields: dict = {
        "headRefOid": head_sha,
        "headRefOidShort": head_sha_short,
    }

    # 2. Check terminal conditions
    if pr_state.get("isTerminal"):
        terminal_reason_raw = pr_state.get("terminalReason", "")
        reason = _TERMINAL_REASON_MAP.get(terminal_reason_raw, "pr_closed")
        result = {
            **base_fields,
            "ready": False,
            "reason": reason,
            "copilotReviewStatus": None,
            "copilotReviewId": None,
            "copilotReviewUrl": None,
            "ciStatus": None,
            "actionRequired": "none",
        }
        return result, head_sha, last_rerun_time

    # 3. Check draft state
    if pr_state.get("isDraft"):
        result = {
            **base_fields,
            "ready": False,
            "reason": "pr_draft",
            "copilotReviewStatus": None,
            "copilotReviewId": None,
            "copilotReviewUrl": None,
            "ciStatus": None,
            "actionRequired": "publish-pr",
        }
        return result, head_sha, last_rerun_time

    # 4. Fetch Copilot review status
    copilot = get_copilot_review_status(pr_number, repo, head_sha)
    copilot_status = copilot.get("status", "unknown")
    copilot_review_id = copilot.get("reviewId")
    copilot_review_url = copilot.get("reviewUrl")

    copilot_fields: dict = {
        "copilotReviewStatus": copilot_status,
        "copilotReviewId": copilot_review_id,
        "copilotReviewUrl": copilot_review_url,
    }

    # 5. Check for Copilot feedback
    if copilot_status in ("has-feedback", "changes-requested"):
        reason = f"copilot_{copilot_status.replace('-', '_')}"
        result = {
            **base_fields,
            **copilot_fields,
            "ready": False,
            "reason": reason,
            "ciStatus": None,
            "actionRequired": "address-copilot-review",
        }
        return result, head_sha, last_rerun_time

    # 6. Fetch CI status
    ci = get_pr_checks_status(pr_number, repo, head_sha)
    ci_status = ci.get("status", "unknown")

    all_fields: dict = {
        **base_fields,
        **copilot_fields,
        "ciStatus": ci_status,
    }

    # 7. Check for stale check re-runs (before declaring failure so
    #    failed/cancelled checks can be re-run when rerun_stale is enabled)
    if _should_rerun_checks(rerun_stale, ci_status, last_rerun_time, poll_interval):
        rerun_result = rerun_failed_checks(pr_number, repo, head_sha)
        rerun_count = len(rerun_result.get("rerunWorkflows", []))
        if rerun_count > 0:
            print(
                f"  Re-running {rerun_count} stale check(s)",
                file=sys.stderr,
            )
            return None, head_sha, time.time()

        # No workflows were actually re-runnable — return a blocking result
        # instead of starting a cooldown that suppresses future rerun attempts.
        result = {
            **all_fields,
            "ready": False,
            "reason": (
                "ci_failed"
                if ci_status == "failed"
                else "ci_cancelled"
                if ci_status == "cancelled"
                else "ci_not_rerunnable"
            ),
            "actionRequired": (
                "investigate-ci-failure"
                if ci_status == "failed"
                else ("investigate-ci-cancellation" if ci_status == "cancelled" else "investigate-ci-status")
            ),
        }
        return result, head_sha, last_rerun_time

    # 8. Check CI failure (only reached when reruns are disabled or on cooldown)
    if ci_status == "failed":
        result = {
            **all_fields,
            "ready": False,
            "reason": "ci_failed",
            "actionRequired": "investigate-ci-failure",
        }
        return result, head_sha, last_rerun_time

    # 9. Check if ready
    if copilot_status == "clean" and ci_status == "all-pass":
        result = {
            **all_fields,
            "ready": True,
            "reason": "copilot_clean_and_ci_green",
            "actionRequired": "approve-and-merge",
        }
        return result, head_sha, last_rerun_time

    # 10. Cancelled CI with reruns disabled is a blocking state
    if ci_status == "cancelled" and not rerun_stale:
        result = {
            **all_fields,
            "ready": False,
            "reason": "ci_cancelled",
            "actionRequired": "rerun-checks",
        }
        return result, head_sha, last_rerun_time

    # 11. Continue polling (CI pending or no Copilot review yet)
    return None, head_sha, last_rerun_time


def _build_error_result(
    pr_number: int,
    repo: str,
    iteration: int,
    total_wait: int,
    stale_checks_rerun: int,
) -> dict:
    """Build an API error result dict."""
    return {
        "prNumber": pr_number,
        "repo": repo,
        "ready": False,
        "reason": "api_error",
        "headRefOid": None,
        "headRefOidShort": None,
        "copilotReviewStatus": None,
        "copilotReviewId": None,
        "copilotReviewUrl": None,
        "ciStatus": None,
        "pollIterations": iteration,
        "totalWaitSeconds": total_wait,
        "staleChecksRerun": stale_checks_rerun,
        "actionRequired": "investigate-api-error",
    }


def _build_timeout_result(
    pr_number: int,
    repo: str,
    iteration: int,
    total_wait: int,
    stale_checks_rerun: int,
    last_copilot_status: str | None,
    last_ci_status: str | None,
    last_head_sha: str | None,
) -> dict:
    """Build a timeout result dict."""
    return {
        "prNumber": pr_number,
        "repo": repo,
        "ready": False,
        "reason": "timeout",
        "headRefOid": last_head_sha,
        "headRefOidShort": last_head_sha[:7] if last_head_sha else None,
        "copilotReviewStatus": last_copilot_status,
        "copilotReviewId": None,
        "copilotReviewUrl": None,
        "ciStatus": last_ci_status,
        "pollIterations": iteration,
        "totalWaitSeconds": total_wait,
        "staleChecksRerun": stale_checks_rerun,
        "actionRequired": "user-decision",
    }


def _write_state_keys(result: dict) -> None:
    """Write poll result state keys for downstream commands."""
    set_value("github.pr_poll_ready_result", result.get("reason", ""))
    set_value("github.pr_poll_ready_action", result.get("actionRequired", ""))


# ---------------------------------------------------------------------------
# Core polling function
# ---------------------------------------------------------------------------


def poll_pr_ready(
    pr_number: int,
    repo: str,
    poll_interval: int = _DEFAULT_POLL_INTERVAL,
    max_wait: int = _DEFAULT_MAX_WAIT,
    rerun_stale_checks: bool = True,
) -> dict:
    """Poll a PR until it is ready to merge or a blocking state is reached.

    This is a **synchronous, blocking** function.  It runs the full polling
    loop to completion and returns a structured result dict.

    Args:
        pr_number: GitHub PR number.
        repo: ``owner/repo`` string.
        poll_interval: Seconds between polls (10–300).
        max_wait: Maximum seconds to wait (30–3600).
        rerun_stale_checks: Auto re-run stale/failed checks.

    Raises:
        ValueError: If *poll_interval* or *max_wait* is outside the allowed
            range.  This mirrors the CLI validation so callers using the
            Python API get a clear error instead of a ``ZeroDivisionError``.

    Returns:
        Structured dict with ``ready``, ``reason``, ``actionRequired``,
        and associated fields.
    """
    if not (_MIN_POLL_INTERVAL <= poll_interval <= _MAX_POLL_INTERVAL):
        raise ValueError(
            f"poll_interval must be between {_MIN_POLL_INTERVAL} and {_MAX_POLL_INTERVAL} seconds; got {poll_interval}."
        )
    if not (_MIN_MAX_WAIT <= max_wait <= _MAX_MAX_WAIT):
        raise ValueError(f"max_wait must be between {_MIN_MAX_WAIT} and {_MAX_MAX_WAIT} seconds; got {max_wait}.")

    max_iterations = max_wait // poll_interval + 1

    iteration = 0
    total_wait = 0
    stale_checks_rerun = 0
    last_rerun_time: float | None = None
    last_head_sha: str | None = None
    consecutive_errors = 0

    for iteration in range(1, max_iterations + 1):
        try:
            result, new_head_sha, new_rerun_time = _evaluate_iteration(
                pr_number, repo, rerun_stale_checks, last_rerun_time, poll_interval
            )
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception as exc:
            consecutive_errors += 1
            print(
                f"[Poll {iteration}/{max_iterations}] Error: {exc}",
                file=sys.stderr,
            )
            if consecutive_errors >= _MAX_CONSECUTIVE_ERRORS:
                error_result = _build_error_result(pr_number, repo, iteration, total_wait, stale_checks_rerun)
                _write_state_keys(error_result)
                return error_result
        else:
            consecutive_errors = 0

            # Track head SHA changes
            if new_head_sha and new_head_sha != last_head_sha:
                if last_head_sha is not None:
                    print(
                        f"  Head SHA changed: {last_head_sha[:7]} -> {new_head_sha[:7]}",
                        file=sys.stderr,
                    )
                    new_rerun_time = None  # Reset re-run cooldown
                last_head_sha = new_head_sha

            # Track re-runs
            if new_rerun_time != last_rerun_time and new_rerun_time is not None:
                stale_checks_rerun += 1
            last_rerun_time = new_rerun_time

            # Check for result
            if result is not None:
                result["prNumber"] = pr_number
                result["repo"] = repo
                result["pollIterations"] = iteration
                result["totalWaitSeconds"] = total_wait
                result["staleChecksRerun"] = stale_checks_rerun
                _write_state_keys(result)
                return result

        # Print status line
        _print_status_line(
            iteration,
            max_iterations,
            total_wait,
        )

        # Sleep if not last iteration
        if iteration < max_iterations:
            time.sleep(poll_interval)
            total_wait += poll_interval

    # Timeout — read last-known statuses from state (written by sibling
    # functions called inside _evaluate_iteration each iteration)
    last_copilot_status = get_value("github.copilot_review_status")
    last_ci_status = get_value("github.pr_checks_status")
    timeout_result = _build_timeout_result(
        pr_number,
        repo,
        iteration,
        total_wait,
        stale_checks_rerun,
        last_copilot_status,
        last_ci_status,
        last_head_sha,
    )
    _write_state_keys(timeout_result)
    return timeout_result


def _print_status_line(
    iteration: int,
    max_iterations: int,
    total_wait: int,
) -> None:
    """Print a concise status line to stderr."""
    print(
        f"[Poll {iteration}/{max_iterations}] wait={total_wait}s",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def pr_poll_ready_command() -> None:
    """CLI entry point for ``agdt-gh-pr-poll-ready``."""
    parser = argparse.ArgumentParser(
        description="Poll a PR until it is ready to merge or reaches a blocking state.",
    )
    parser.add_argument(
        "--pr",
        type=int,
        default=None,
        help="PR number (falls back to github.pull_request_number in state)",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="owner/repo (falls back to github.repo in state or git remote)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=_DEFAULT_POLL_INTERVAL,
        help=(
            f"Seconds between polls (default: {_DEFAULT_POLL_INTERVAL}, "
            f"range: {_MIN_POLL_INTERVAL}-{_MAX_POLL_INTERVAL})"
        ),
    )
    parser.add_argument(
        "--max-wait",
        type=int,
        default=_DEFAULT_MAX_WAIT,
        help=f"Maximum seconds to wait (default: {_DEFAULT_MAX_WAIT}, range: {_MIN_MAX_WAIT}-{_MAX_MAX_WAIT})",
    )
    parser.add_argument(
        "--background",
        action="store_true",
        default=False,
        help="Run as a background task",
    )
    parser.add_argument(
        "--rerun-stale-checks",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Auto re-run stale/failed checks (default: True)",
    )

    args = parser.parse_args()

    # Resolve PR number
    pr_number = args.pr
    if pr_number is None:
        pr_val = get_value("github.pull_request_number")
        if pr_val is not None:
            try:
                pr_number = int(pr_val)
            except (ValueError, TypeError):
                pass
    if pr_number is None:
        print(
            "Error: PR number is required. Provide --pr <number> or set github.pull_request_number in state.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Resolve repo
    repo = resolve_github_repo(args.repo)

    # Validate poll_interval
    if not (_MIN_POLL_INTERVAL <= args.poll_interval <= _MAX_POLL_INTERVAL):
        print(
            f"Error: --poll-interval must be between "
            f"{_MIN_POLL_INTERVAL} and {_MAX_POLL_INTERVAL} seconds (got {args.poll_interval}).",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate max_wait
    if not (_MIN_MAX_WAIT <= args.max_wait <= _MAX_MAX_WAIT):
        print(
            f"Error: --max-wait must be between {_MIN_MAX_WAIT} and {_MAX_MAX_WAIT} seconds (got {args.max_wait}).",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.background:
        from ...background_tasks import run_function_in_background
        from ...task_state import print_task_tracking_info

        task = run_function_in_background(
            module_path="agentic_devtools.cli.github.pr_poll_ready",
            function_name="poll_pr_ready",
            command_display_name="agdt-gh-pr-poll-ready",
            args={
                "pr_number": pr_number,
                "repo": repo,
                "poll_interval": args.poll_interval,
                "max_wait": args.max_wait,
                "rerun_stale_checks": args.rerun_stale_checks,
            },
        )
        print_task_tracking_info(task, f"Polling PR #{pr_number} for merge readiness")
        return

    result = poll_pr_ready(
        pr_number=pr_number,
        repo=repo,
        poll_interval=args.poll_interval,
        max_wait=args.max_wait,
        rerun_stale_checks=args.rerun_stale_checks,
    )
    print(json.dumps(result, indent=2))
