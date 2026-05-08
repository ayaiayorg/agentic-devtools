"""Top-level orchestrator for the finalization pass.

Sequences phases 0–9: identity resolution, thread fetch, classification,
convergence computation, batch repair, verification, targeted fallback,
retry, and reporting.
"""

from __future__ import annotations

import sys
import time
from typing import Any

from ..config import AzureDevOpsConfig
from ..review_state import ReviewState
from .classification import classify_eligible_comments
from .convergence import check_convergence, compute_expected_content
from .identity import resolve_pat_identity
from .models import EligibleComments, FinalizationReport
from .repair import batch_repair_pass, targeted_repair
from .reporting import build_finalization_report, emit_report_summary, persist_report
from .verification import verify_convergence

# Maximum total duration for the finalization pass (seconds)
_TIMEOUT_SECONDS = 60
# Maximum number of retry rounds for targeted fallback
_MAX_RETRY_ROUNDS = 2
# Delay between retry rounds (seconds)
_RETRY_DELAY_SECONDS = 5


def run_finalization_pass(
    review_state: ReviewState,
    pr_id: int,
    config: AzureDevOpsConfig,
    headers: dict[str, str],
    dry_run: bool = False,
) -> FinalizationReport:
    """Run the full finalization pass on AGDT-generated PR comments.

    Orchestrates: identity resolution → thread fetch → classification →
    convergence check → batch repair → verification → targeted fallback →
    retry → reporting.

    This function is designed to be **non-blocking**: any exception is caught
    and reported rather than propagated.  Missing or corrupt review state
    results in a no-op success report.

    Args:
        review_state: Current review state (source of truth, may be mutated).
        pr_id: Pull request ID.
        config: Azure DevOps configuration.
        headers: Auth headers for API calls.
        dry_run: If True, run classification + convergence check without
            mutations.

    Returns:
        FinalizationReport with counts and details.
    """
    start_time = time.monotonic()
    details: list[str] = []

    try:
        # Phase 0: Resolve PAT identity
        organization = config.organization
        pat_user_id = resolve_pat_identity(organization, headers)
        if pat_user_id is None:
            details.append("PAT identity resolution failed — no mutations performed")
            return _build_report("skipped", 0, 0, 0, 0, details, start_time)

        # Phase 1: Fetch current threads from API
        threads = _fetch_threads(config, headers, review_state.repoId, pr_id)
        if threads is None:
            details.append("Could not fetch PR threads")
            return _build_report("skipped", 0, 0, 0, 0, details, start_time)

        # Phase 2: Classify eligible comments
        eligible = classify_eligible_comments(threads, pat_user_id, review_state)
        total_eligible = _count_eligible(eligible)
        if total_eligible == 0:
            details.append("No eligible AGDT comments found")
            if eligible.skipped:
                for skip in eligible.skipped:
                    details.append(f"Skipped: thread {skip.get('thread_id', '?')}: {skip.get('reason', 'unknown')}")
            return _build_report("no-op", 0, len(eligible.skipped), 0, 0, details, start_time)

        # Phase 3: Compute expected terminal content
        from ..review_scaffold import build_pr_base_url

        base_url = build_pr_base_url(config, pr_id)
        expected_map: dict[int, str] = {}
        all_comments = _collect_all_comments(eligible)
        for comment in all_comments:
            expected_map[comment.comment_id] = compute_expected_content(comment, review_state, base_url)

        # Phase 4: Check initial convergence
        unchanged = 0
        non_converged = []
        for comment in all_comments:
            expected = expected_map.get(comment.comment_id, "")
            if check_convergence(comment, expected):
                unchanged += 1
            else:
                non_converged.append(comment)

        if not non_converged:
            details.append("All comments already in terminal state")
            if eligible.skipped:
                for skip in eligible.skipped:
                    details.append(f"Skipped: thread {skip.get('thread_id', '?')}: {skip.get('reason', 'unknown')}")
            return _build_report("no-op", 0, len(eligible.skipped), unchanged, 0, details, start_time)

        # Phase 5: Batch-first repair
        if not dry_run:
            batch_result = batch_repair_pass(
                eligible,
                review_state,
                config,
                headers,
                pr_id,
                base_url,
                dry_run=False,
            )
            details.append(f"Batch repair: {batch_result.succeeded}/{batch_result.attempted} succeeded")
            if batch_result.errors:
                for err in batch_result.errors:
                    details.append(f"Batch error: {err}")
        else:
            details.append(f"Dry run: {len(non_converged)} comments would be repaired")
            return _build_report(
                "success",
                len(non_converged),
                len(eligible.skipped),
                unchanged,
                0,
                details,
                start_time,
            )

        # Phase 6-8: Verification and retry
        repaired = 0
        failed = 0
        for round_num in range(_MAX_RETRY_ROUNDS + 1):
            if _check_timeout(start_time):
                details.append(f"Timeout reached after {_TIMEOUT_SECONDS}s")
                break

            # Verify convergence
            convergence_results = verify_convergence(
                eligible,
                expected_map,
                config,
                headers,
                pr_id,
                review_state.repoId,
            )

            still_non_converged = [cr.comment for cr in convergence_results if not cr.converged]
            newly_converged = len(convergence_results) - len(still_non_converged)
            repaired += newly_converged - unchanged
            unchanged = 0  # Only count on first pass

            if not still_non_converged:
                details.append("All comments converged after verification")
                break

            if round_num < _MAX_RETRY_ROUNDS:
                # Targeted fallback
                details.append(
                    f"Round {round_num + 1}: {len(still_non_converged)} "
                    "comments non-converged, applying targeted repair"
                )
                targeted_result = targeted_repair(
                    still_non_converged,
                    expected_map,
                    config,
                    headers,
                    pr_id,
                    review_state,
                )
                if targeted_result.errors:
                    for err in targeted_result.errors:
                        details.append(f"Targeted repair error: {err}")

                time.sleep(_RETRY_DELAY_SECONDS)
            else:
                failed = len(still_non_converged)
                details.append(f"Max retries reached: {failed} comments still non-converged")

        # Add skipped info
        if eligible.skipped:
            for skip in eligible.skipped:
                details.append(f"Skipped: thread {skip.get('thread_id', '?')}: {skip.get('reason', 'unknown')}")

        # Determine final status
        if failed > 0:
            status = "partial" if repaired > 0 else "failure"
        else:
            status = "success"

        return _build_report(status, repaired, len(eligible.skipped), 0, failed, details, start_time)

    except Exception as exc:
        details.append(f"Finalization error: {exc}")
        print(f"Warning: Finalization pass failed: {exc}", file=sys.stderr)
        return _build_report("failure", 0, 0, 0, 0, details, start_time)


def _build_report(
    status: str,
    repaired: int,
    skipped: int,
    unchanged: int,
    failed: int,
    details: list[str],
    start_time: float,
) -> FinalizationReport:
    """Build a finalization report with duration calculation."""
    duration_ms = int((time.monotonic() - start_time) * 1000)
    report = build_finalization_report(status, repaired, skipped, unchanged, failed, details, duration_ms)

    # Persist and emit
    try:
        from ...state import get_state_dir

        state_dir = get_state_dir()
        commit_hash_short = "unknown"
        persist_report(report, state_dir, commit_hash_short)
    except Exception:
        pass  # Non-critical

    emit_report_summary(report)
    return report


def _fetch_threads(
    config: AzureDevOpsConfig,
    headers: dict[str, str],
    repo_id: str,
    pr_id: int,
) -> list[dict] | None:
    """Fetch all threads for a PR from the Azure DevOps API."""
    try:
        from ..helpers import require_requests

        requests_module: Any = require_requests()
        url = config.build_api_url(repo_id, "pullRequests", pr_id, "threads")
        response = requests_module.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("value", [])
    except Exception as exc:
        print(f"Warning: Could not fetch PR threads: {exc}", file=sys.stderr)
        return None


def _count_eligible(eligible: EligibleComments) -> int:
    """Count total eligible comments."""
    count = len(eligible.file_summaries)
    if eligible.overall_summary is not None:
        count += 1
    count += len(eligible.activity_log_entries)
    return count


def _collect_all_comments(eligible: EligibleComments) -> list:
    """Collect all eligible comments into a flat list."""
    from .verification import _collect_all_comments as _collect

    return _collect(eligible)


def _check_timeout(start_time: float) -> bool:
    """Check if the finalization pass has exceeded the timeout."""
    elapsed = time.monotonic() - start_time
    return elapsed >= _TIMEOUT_SECONDS
