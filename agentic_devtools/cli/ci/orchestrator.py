"""AI PR loop orchestrator.

State machine extracted from ai-pr-loop.yml. Implements:
metadata resolution → guards → CI status check → review evaluation →
repair dispatch → approval → merge.

When actionable Copilot review comments or failing CI checks are detected,
the orchestrator dispatches a repair by posting a @copilot-tagged comment
on the PR (FR-001, FR-002). When everything is green, it approves and merges.
"""

from __future__ import annotations

import json
import logging
import sys

from agentic_devtools.cli.ci.github_provider import COPILOT_LOGINS
from agentic_devtools.cli.ci.guards import (
    check_cycle_limit,
    check_deduplication,
    check_docker_files,
    check_exclusion_labels,
    check_fork_pr,
    check_privileged_paths,
)
from agentic_devtools.cli.ci.models import EventPayload, RepairDecision
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)

# Exit codes
EXIT_SUCCESS = 0
EXIT_GUARD_BLOCKED = 1
EXIT_MALFORMED_EVENT = 2
EXIT_MERGE_BLOCKED = 3
EXIT_METADATA_FAILED = 4
EXIT_REPAIR_DISPATCHED = 5

# Default check run names to exclude from CI gating (self-referencing workflows)
_DEFAULT_EXCLUDED_CHECK_NAMES = frozenset(
    {
        "AI PR Loop",
        "Generate lint fix patch",
    }
)


def run_ai_pr_loop(
    provider: CIPlatformProvider,
    event_payload: EventPayload,
    *,
    excluded_check_names: frozenset[str] | None = None,
) -> int:
    """Run the AI PR loop state machine.

    Implements the full orchestration sequence:
    1. Validate event payload
    2. Resolve PR metadata
    3. Evaluate guards (privileged paths, Docker, fork, labels, dedup, cycle)
    4. Check CI status
    5. Evaluate reviews
    6. Decide: dispatch repair, approve, or merge

    When actionable Copilot review comments (CHANGES_REQUESTED) or failing
    CI checks are detected, a @copilot-tagged comment is posted to trigger
    an AI agent repair session (FR-001, FR-002).

    Args:
        provider: CI platform provider for API interactions.
        event_payload: Normalized event payload from the trigger.
        excluded_check_names: Optional set of check run names to exclude from
            CI gating (self-referencing workflows). Defaults to
            ``_DEFAULT_EXCLUDED_CHECK_NAMES`` if not provided.

    Returns:
        Exit code (0 = success, non-zero = blocked/error).
    """
    if excluded_check_names is None:
        excluded_check_names = _DEFAULT_EXCLUDED_CHECK_NAMES
    # Step 1: Validate we have a PR to work with
    if event_payload.pr_number == 0:
        logger.warning("No PR number in event payload, skipping")
        return EXIT_SUCCESS

    pr_number = event_payload.pr_number

    # Step 2: Resolve full PR metadata
    try:
        pr_meta = provider.get_pr_metadata(pr_number)
    except Exception as exc:
        logger.error("Failed to get PR metadata for #%d: %s", pr_number, exc)
        _emit_error({"error": "metadata_resolution_failed", "pr_number": pr_number, "detail": str(exc)})
        return EXIT_METADATA_FAILED

    # Step 3: Evaluate guards
    # 3a: Fork PR guard
    if check_fork_pr(pr_meta.head_repo_full_name, pr_meta.base_repo_full_name):
        logger.info("PR #%d is from a fork — skipping", pr_number)
        return EXIT_GUARD_BLOCKED

    # 3b: Exclusion labels
    should_skip, flag = check_exclusion_labels(pr_meta.labels)
    if should_skip:
        logger.info("PR #%d has exclusion label — skipping entirely", pr_number)
        return EXIT_GUARD_BLOCKED

    do_not_merge = flag == "do_not_merge"

    # 3c: Privileged paths
    files = provider.list_pr_files(pr_number)
    if check_privileged_paths(files):
        logger.info("PR #%d touches privileged paths — requires human review", pr_number)
        return EXIT_GUARD_BLOCKED

    # 3d: Docker files
    if check_docker_files(files):
        logger.info("PR #%d touches Docker files — requires human review", pr_number)
        return EXIT_GUARD_BLOCKED

    # Step 4: Check CI status
    check_runs = provider.list_check_runs(pr_meta.head_sha)
    has_unknown_conclusion = False
    any_failed = False
    any_pending = False
    failed_checks = []
    for cr in check_runs:
        # Skip self-referencing workflows to avoid deadlock
        if cr.name in excluded_check_names:
            continue
        if cr.status != "completed":
            any_pending = True
        elif cr.conclusion == "failure":
            any_failed = True
            failed_checks.append(cr)
        elif cr.conclusion not in ("success", "neutral", "skipped"):
            has_unknown_conclusion = True

    if any_pending:
        logger.info("PR #%d has pending checks — waiting", pr_number)
        return EXIT_SUCCESS

    # 3e: Deduplication — checked after CI pending short-circuit so that
    # re-triggers while CI is still running don't consume the dispatch budget.
    dedup_sha = event_payload.head_sha or pr_meta.head_sha
    dedup_skip, dedup_count = check_deduplication(provider, pr_number, dedup_sha)
    if dedup_skip:
        logger.info("PR #%d dispatch limit reached (count=%d) — skipping", pr_number, dedup_count)
        return EXIT_GUARD_BLOCKED

    # 3f: Cycle limit — checked after CI pending short-circuit so that
    # re-triggers while CI is still running don't exhaust the cycle budget.
    cycle_reached, cycle_count = check_cycle_limit(provider, pr_number)
    if cycle_reached:
        logger.info("PR #%d cycle limit reached (count=%d) — skipping", pr_number, cycle_count)
        return EXIT_GUARD_BLOCKED

    # Step 5: Evaluate reviews
    reviews = provider.list_reviews(pr_number)
    has_approval = any(r.state == "APPROVED" for r in reviews)
    has_changes_requested = False
    copilot_review_id = 0

    # Detect actionable Copilot review comments (CHANGES_REQUESTED with inline comments)
    for review in reviews:
        if review.state == "CHANGES_REQUESTED" and review.user in COPILOT_LOGINS:
            has_changes_requested = True
            copilot_review_id = review.id
            break
        if review.state == "CHANGES_REQUESTED":
            has_changes_requested = True

    # Step 6: Dispatch repair decision
    decision = _evaluate_repair_decision(
        any_failed=any_failed,
        has_changes_requested=has_changes_requested,
        copilot_review_id=copilot_review_id,
        failed_checks=failed_checks,
    )

    if decision.repair_needed:
        return _dispatch_repair(
            provider=provider,
            pr_number=pr_number,
            head_sha=pr_meta.head_sha,
            decision=decision,
        )

    # Step 7: Merge gate
    if any_failed:
        logger.info("PR #%d has failed checks — merge blocked", pr_number)
        return EXIT_MERGE_BLOCKED

    if has_unknown_conclusion:
        logger.info(
            "PR #%d has checks with non-success conclusions — cannot merge",
            pr_number,
        )
        return EXIT_MERGE_BLOCKED

    if has_changes_requested:
        logger.info("PR #%d has changes requested — waiting for updates", pr_number)
        return EXIT_SUCCESS

    if do_not_merge:
        logger.info("PR #%d ready but do-not-auto-merge label present", pr_number)
        return EXIT_SUCCESS

    # Step 8: Approve if needed
    if not has_approval:
        provider.approve_pr(pr_number, pr_meta.head_sha, "Auto-approved by AI PR loop")

    # Step 9: Merge
    try:
        provider.merge_pr(pr_number, pr_meta.head_sha, "squash")
        logger.info("PR #%d merged successfully", pr_number)
    except Exception as exc:
        logger.error("Failed to merge PR #%d: %s", pr_number, exc)
        return EXIT_MERGE_BLOCKED

    return EXIT_SUCCESS


def _evaluate_repair_decision(
    *,
    any_failed: bool,
    has_changes_requested: bool,
    copilot_review_id: int,
    failed_checks: list,
) -> RepairDecision:
    """Evaluate whether a repair dispatch is needed and determine the type.

    Args:
        any_failed: True if any CI check has failed.
        has_changes_requested: True if any review requests changes.
        copilot_review_id: ID of the Copilot review (0 if none).
        failed_checks: List of failed check runs.

    Returns:
        RepairDecision indicating whether and what type of repair is needed.
    """
    has_review_repair = has_changes_requested
    has_ci_repair = any_failed

    if not has_review_repair and not has_ci_repair:
        return RepairDecision(repair_needed=False)

    if has_review_repair and has_ci_repair:
        repair_type = "both"
    elif has_review_repair:
        repair_type = "review"
    else:
        repair_type = "ci"

    return RepairDecision(
        repair_needed=True,
        repair_type=repair_type,
        review_id=copilot_review_id,
        failed_checks=failed_checks,
    )


def _dispatch_repair(
    *,
    provider: CIPlatformProvider,
    pr_number: int,
    head_sha: str,
    decision: RepairDecision,
) -> int:
    """Dispatch repair by posting a @copilot comment on the PR.

    Collects review comment bodies when a Copilot review triggered the
    repair, then posts a @copilot-tagged comment to trigger an AI agent
    repair session.

    Args:
        provider: CI platform provider for API interactions.
        pr_number: Pull request number.
        head_sha: Current HEAD SHA.
        decision: Repair decision with type and context.

    Returns:
        EXIT_REPAIR_DISPATCHED on success, EXIT_MERGE_BLOCKED on failure.
    """
    # Collect review comment bodies when review repair is needed
    review_comments: list[str] = []
    if decision.review_id and decision.repair_type in ("review", "both"):
        try:
            review_comments = provider.list_review_comments(pr_number, decision.review_id)
        except Exception as exc:
            logger.warning("Failed to fetch review comments for PR #%d: %s", pr_number, exc)

    try:
        comment_id = provider.dispatch_repair(
            pr_number=pr_number,
            head_sha=head_sha,
            repair_type=decision.repair_type,
            failed_checks=decision.failed_checks,
            review_comments=review_comments,
        )
        logger.info(
            "PR #%d repair dispatched (type=%s, comment_id=%d)",
            pr_number,
            decision.repair_type,
            comment_id,
        )
        return EXIT_REPAIR_DISPATCHED
    except Exception as exc:
        logger.error("Failed to dispatch repair for PR #%d: %s", pr_number, exc)
        return EXIT_MERGE_BLOCKED


def _emit_error(error_data: dict) -> None:
    """Emit structured error JSON to stderr."""
    json.dump(error_data, sys.stderr)
    sys.stderr.write("\n")
