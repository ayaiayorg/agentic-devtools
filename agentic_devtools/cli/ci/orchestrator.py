"""AI PR loop orchestrator.

Minimal state machine extracted from ai-pr-loop.yml. Currently implements:
metadata resolution → guards → CI status check → review evaluation →
approval → merge.

Not yet implemented: repair dispatch, comment templates, CI polling loops.
These will be added in subsequent phases.
"""

from __future__ import annotations

import json
import logging
import sys

from agentic_devtools.cli.ci.guards import (
    check_cycle_limit,
    check_deduplication,
    check_docker_files,
    check_exclusion_labels,
    check_fork_pr,
    check_privileged_paths,
)
from agentic_devtools.cli.ci.models import EventPayload
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)

# Exit codes
EXIT_SUCCESS = 0
EXIT_GUARD_BLOCKED = 1
EXIT_MALFORMED_EVENT = 2
EXIT_MERGE_BLOCKED = 3
EXIT_METADATA_FAILED = 4

# Default check run names to exclude from CI gating (self-referencing workflows)
_DEFAULT_EXCLUDED_CHECK_NAMES = frozenset({
    "AI PR Loop",
    "Generate lint fix patch",
})


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
    for cr in check_runs:
        # Skip self-referencing workflows to avoid deadlock
        if cr.name in excluded_check_names:
            continue
        if cr.status != "completed":
            any_pending = True
        elif cr.conclusion == "failure":
            any_failed = True
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

    if any_failed:
        logger.info("PR #%d has failed checks — merge blocked", pr_number)
        return EXIT_MERGE_BLOCKED

    # Step 5: Evaluate reviews
    reviews = provider.list_reviews(pr_number)
    has_approval = any(r.state == "APPROVED" for r in reviews)
    has_changes_requested = any(r.state == "CHANGES_REQUESTED" for r in reviews)

    if has_changes_requested:
        logger.info("PR #%d has changes requested — waiting for updates", pr_number)
        return EXIT_SUCCESS

    # Step 6: Merge gate
    if has_unknown_conclusion:
        logger.info("PR #%d has checks with non-success conclusions (e.g., cancelled, timed_out) — cannot merge", pr_number)
        return EXIT_MERGE_BLOCKED

    if do_not_merge:
        logger.info("PR #%d ready but do-not-auto-merge label present", pr_number)
        return EXIT_SUCCESS

    # Step 7: Approve if needed
    if not has_approval:
        provider.approve_pr(pr_number, pr_meta.head_sha, "Auto-approved by AI PR loop")

    # Step 8: Merge
    try:
        provider.merge_pr(pr_number, pr_meta.head_sha, "squash")
        logger.info("PR #%d merged successfully", pr_number)
    except Exception as exc:
        logger.error("Failed to merge PR #%d: %s", pr_number, exc)
        return EXIT_MERGE_BLOCKED

    return EXIT_SUCCESS


def _emit_error(error_data: dict) -> None:
    """Emit structured error JSON to stderr."""
    json.dump(error_data, sys.stderr)
    sys.stderr.write("\n")
