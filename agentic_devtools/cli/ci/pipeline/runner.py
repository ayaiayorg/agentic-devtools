"""Pipeline runner — executes actions sequentially with guard-blocking."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone

from agentic_devtools.cli.ci.logging_config import is_github_actions
from agentic_devtools.cli.ci.pipeline.base import Action
from agentic_devtools.cli.ci.pipeline.models import (
    ActionDecision,
    ActionResult,
    PipelineRunSummary,
)
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)


def _log_group(title: str) -> None:
    """Emit a ::group:: annotation when running in GitHub Actions."""
    if is_github_actions():
        print(f"::group::{title}", file=sys.stderr, flush=True)


def _log_endgroup() -> None:
    """Emit an ::endgroup:: annotation when running in GitHub Actions."""
    if is_github_actions():
        print("::endgroup::", file=sys.stderr, flush=True)


def _get_run_url() -> str:
    """Build the GitHub Actions run URL from environment variables."""
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if repository and run_id:
        return f"{server_url}/{repository}/actions/runs/{run_id}"
    return ""


def run_pipeline(
    provider: CIPlatformProvider,
    snapshot: PRStateSnapshot,
    actions: list[Action],
) -> PipelineRunSummary:
    """Execute the action pipeline sequentially.

    Each action is evaluated against the current state. If Guards (action 0)
    returns BLOCKED, all subsequent actions are marked BLOCKED_BY_GUARD.

    Args:
        provider: CI platform provider for API interactions.
        snapshot: Immutable PR state snapshot.
        actions: Ordered list of actions to evaluate and execute.

    Returns:
        PipelineRunSummary with all action results.
    """
    derived = DerivedState(snapshot)
    results: list[ActionResult] = []
    guard_blocked = False
    guard_block_reason = ""
    # Name of the first side-effecting action that returned FAILED; empty when none.
    exec_failed_by = ""
    snapshot_invalidated_by = ""

    for action in actions:
        action_name = action.name
        _log_group(f"Action: {action_name}")

        if guard_blocked:
            result = ActionResult(
                name=action_name,
                decision=ActionDecision.BLOCKED_BY_GUARD,
                details=f"Blocked by guards: {guard_block_reason}",
            )
            logger.info(
                "Action '%s': BLOCKED_BY_GUARD (reason: %s)",
                action_name,
                guard_block_reason,
            )
            results.append(result)
            _log_endgroup()
            continue

        # If a prior side-effecting action failed, skip this action entirely
        # (including evaluation) to prevent unsafe cascades.
        if exec_failed_by:
            result = ActionResult(
                name=action_name,
                decision=ActionDecision.SKIP,
                details=f"Pipeline halted: '{exec_failed_by}' failed",
            )
            logger.info(
                "Action '%s': SKIP (halted by prior failure in '%s')",
                action_name,
                exec_failed_by,
            )
            results.append(result)
            _log_endgroup()
            continue

        if snapshot_invalidated_by:
            result = ActionResult(
                name=action_name,
                decision=ActionDecision.SKIP,
                details=(f"Pipeline halted: '{snapshot_invalidated_by}' changed PR HEAD; rerun required"),
            )
            logger.info(
                "Action '%s': SKIP (halted by snapshot invalidation in '%s')",
                action_name,
                snapshot_invalidated_by,
            )
            results.append(result)
            _log_endgroup()
            continue

        # Evaluate preconditions
        try:
            eval_result = action.evaluate(snapshot, derived)
        except Exception as exc:
            logger.error("Action '%s' evaluation raised exception: %s", action_name, exc)
            result = ActionResult(
                name=action_name,
                decision=ActionDecision.FAILED,
                error=str(exc),
                details="Exception during evaluation",
            )
            # Guards fail closed
            if action_name == "guards":
                guard_blocked = True
                guard_block_reason = f"evaluation_exception: {exc}"
                result.decision = ActionDecision.BLOCKED
                result.details = f"Exception during evaluation: {exc}"
            else:
                exec_failed_by = action_name
            results.append(result)
            _log_endgroup()
            continue

        logger.info(
            "Action '%s': evaluated → %s (preconditions: %s)",
            action_name,
            eval_result.decision.value,
            eval_result.preconditions,
        )

        if eval_result.decision == ActionDecision.BLOCKED:
            # Guards action blocking the rest
            if action_name == "guards":
                guard_blocked = True
                guard_block_reason = eval_result.details
            results.append(eval_result)
            _log_endgroup()
            continue

        if eval_result.decision != ActionDecision.EXECUTE:
            # SKIP or other non-execute decision
            results.append(eval_result)
            _log_endgroup()
            continue

        # Execute the action
        try:
            exec_result = action.execute(provider, snapshot, derived)
            logger.info(
                "Action '%s': executed → %s (details: %s)",
                action_name,
                exec_result.decision.value,
                exec_result.details,
            )
            # Merge preconditions from evaluation into execution result
            if not exec_result.preconditions and eval_result.preconditions:
                exec_result.preconditions = eval_result.preconditions
            results.append(exec_result)
            # Track first FAILED side-effect to block subsequent executions
            if exec_result.decision == ActionDecision.FAILED and action_name != "guards":
                exec_failed_by = action_name
            if exec_result.invalidates_snapshot:
                snapshot_invalidated_by = action_name
        except Exception as exc:
            logger.error("Action '%s' execution raised exception: %s", action_name, exc)
            result = ActionResult(
                name=action_name,
                decision=ActionDecision.FAILED,
                preconditions=eval_result.preconditions,
                error=str(exc),
                details="Exception during execution",
            )
            results.append(result)
            if action_name != "guards":
                exec_failed_by = action_name

        _log_endgroup()

    return PipelineRunSummary(
        results=results,
        snapshot=snapshot,
        run_url=_get_run_url(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
