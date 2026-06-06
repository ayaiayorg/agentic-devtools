"""Pipeline command entry point — replaces the event-branching orchestrator."""

from __future__ import annotations

import logging

from agentic_devtools.cli.ci.evaluator.lock import acquire_lock, release_lock
from agentic_devtools.cli.ci.models import EventPayload
from agentic_devtools.cli.ci.pipeline.actions import (
    ApplySuggestionsAction,
    ApproveAction,
    DispatchRepairAction,
    GuardsAction,
    MergeAction,
    PublishAction,
    RebaseAction,
    RequestReviewAction,
    ResolveThreadsAction,
    SquashAction,
)
from agentic_devtools.cli.ci.pipeline.base import Action
from agentic_devtools.cli.ci.pipeline.models import ActionDecision, ActionResult
from agentic_devtools.cli.ci.pipeline.runner import run_pipeline
from agentic_devtools.cli.ci.pipeline.snapshot import PRStateSnapshot, build_pr_state_snapshot
from agentic_devtools.cli.ci.pipeline.summary import post_summary_comment
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)

# Exit codes (same as orchestrator.py for compatibility)
EXIT_SUCCESS = 0
EXIT_GUARD_BLOCKED = 1
EXIT_MERGE_BLOCKED = 3
EXIT_METADATA_FAILED = 4
EXIT_REPAIR_DISPATCHED = 5


def run_ai_pr_loop_v2(
    provider: CIPlatformProvider,
    event_payload: EventPayload,
    *,
    actionable_check_names: frozenset[str] | None = None,
) -> int:
    """Run the idempotent AI PR loop pipeline.

    Replaces the event-branching orchestrator with a sequential pipeline
    of 10 action evaluators. Every run evaluates all actions regardless of
    trigger type.

    Pipeline ordering:
        Guards → Publish → ApplySuggestions → DispatchRepair → ResolveThreads
        → Squash → Rebase → RequestReview → Approve → Merge

    ApplySuggestions runs before DispatchRepair so that autofixable suggestions
    are committed first, potentially eliminating the need for repair dispatch.

    ResolveThreads runs before RequestReview so that resolved threads are reflected in
    derived state before the review-request guard evaluates unresolved_threads.

    Args:
        provider: CI platform provider for API interactions.
        event_payload: Normalized event payload from the trigger.
        actionable_check_names: Optional set of check run names to evaluate.

    Returns:
        Exit code (0 = success, non-zero = blocked/error).
    """
    pr_number = event_payload.pr_number
    if pr_number == 0:
        logger.warning("No PR number in event payload, skipping")
        return EXIT_SUCCESS

    # Acquire evaluator lock first so that races resolve without burning snapshot
    # API quota on runs that will be discarded.
    lock_token: str | None = None
    try:
        lock_token = acquire_lock(provider, pr_number)
    except Exception as exc:
        logger.warning("PR #%d: Failed to acquire lock: %s", pr_number, exc)
        return EXIT_METADATA_FAILED

    if lock_token is None:
        logger.info("PR #%d: Lock already held — skipping pipeline run", pr_number)
        return EXIT_SUCCESS

    try:
        # Build PR state snapshot (after the lock so only the winner pays the cost)
        try:
            snapshot = build_pr_state_snapshot(
                provider,
                pr_number,
                actionable_check_names=actionable_check_names,
            )
        except Exception as exc:
            logger.error("Failed to build PR state snapshot for #%d: %s", pr_number, exc)
            return EXIT_METADATA_FAILED

        # Build action pipeline
        actions: list[Action] = [
            GuardsAction(),
            PublishAction(),
            ApplySuggestionsAction(),
            DispatchRepairAction(),
            ResolveThreadsAction(),
            SquashAction(),
            RebaseAction(),
            RequestReviewAction(),
            ApproveAction(),
            MergeAction(),
        ]

        # Run pipeline
        summary = run_pipeline(provider, snapshot, actions)

        # Post summary comment
        post_summary_comment(provider, pr_number, summary)

        # Determine exit code from results
        return _determine_exit_code(summary.results, snapshot=summary.snapshot)

    finally:
        # Release lock
        try:
            release_lock(provider, pr_number, lock_token)
        except Exception as exc:
            logger.warning("PR #%d: Failed to release lock: %s", pr_number, exc)


def _determine_exit_code(results: list[ActionResult], *, snapshot: PRStateSnapshot | None = None) -> int:
    """Determine the exit code from pipeline results."""
    repair_dispatched = False
    failed_side_effect_action = False
    side_effect_actions = {
        "apply_suggestions",
        "publish",
        "request_review",
        "resolve_threads",
        "dispatch_repair",
        "squash",
        "rebase",
        "approve",
        "merge",
    }

    for result in results:
        if result.decision == ActionDecision.BLOCKED:
            return EXIT_GUARD_BLOCKED
        if result.name == "dispatch_repair":
            if result.decision == ActionDecision.EXECUTE:
                repair_dispatched = True
            elif result.limit_reached:
                # Dedup or cycle limit reached — treat as guard-blocked (same as legacy orchestrator)
                return EXIT_GUARD_BLOCKED
        if (
            result.name == "approve"
            and result.decision == ActionDecision.SKIP
            and not result.preconditions.get("approver_token_available", True)
        ):
            # Provider could not submit approval (missing approver token).  Block merge so
            # the workflow retries rather than silently exiting 0 with the PR unmerged.
            return EXIT_MERGE_BLOCKED
        if result.decision == ActionDecision.FAILED and result.name in side_effect_actions:
            failed_side_effect_action = True

    if repair_dispatched:
        return EXIT_REPAIR_DISPATCHED
    if failed_side_effect_action:
        return EXIT_MERGE_BLOCKED
    if snapshot is not None and snapshot.ci_status == "unknown":
        return EXIT_MERGE_BLOCKED
    return EXIT_SUCCESS
