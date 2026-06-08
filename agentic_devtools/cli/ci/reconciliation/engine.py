"""Reconciliation engine for retrying failed workflow runs.

The ``reconcile()`` function is the main entry point. It:
1. Queries the provider for recent workflow runs
2. Filters to retriable conclusions within the configured window
3. Selects the oldest run still under the retry cap
4. Escalates only when all eligible runs are maxed out
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from agentic_devtools.cli.ci.provider import CIPlatformProvider
from agentic_devtools.cli.ci.reconciliation.config import (
    MAX_RUN_ATTEMPTS,
    RECONCILIATION_WINDOW_HOURS,
    RETRIABLE_CONCLUSIONS,
)
from agentic_devtools.cli.ci.reconciliation.context_mapper import map_run_context
from agentic_devtools.cli.ci.reconciliation.exceptions import UnmappableContextError
from agentic_devtools.cli.ci.reconciliation.models import (
    ReconciliationAction,
    ReconciliationResult,
    RunEventContext,
    WorkflowRun,
)

logger = logging.getLogger(__name__)


def reconcile(
    provider: CIPlatformProvider,
    workflow_id: str,
    *,
    max_run_attempts: int | None = None,
    window_hours: int | None = None,
) -> ReconciliationResult:
    """Run the reconciliation engine for a given workflow.

    Queries the provider for recent failed runs, retries the oldest run still
    under the attempt cap, and escalates only when no eligible run can be retried.

    Args:
        provider: CI platform provider instance.
        workflow_id: Workflow file name or ID to reconcile.
        max_run_attempts: Override for MAX_RUN_ATTEMPTS config.
        window_hours: Override for RECONCILIATION_WINDOW_HOURS config.

    Returns:
        ReconciliationResult describing what action was taken.
    """
    effective_max_attempts = max_run_attempts if max_run_attempts is not None else MAX_RUN_ATTEMPTS
    effective_window = window_hours if window_hours is not None else RECONCILIATION_WINDOW_HOURS

    logger.info(
        "Reconciling workflow %r (max_attempts=%d, window=%dh)",
        workflow_id,
        effective_max_attempts,
        effective_window,
    )

    # Get all runs from the provider (provider handles window filtering)
    runs = provider.list_workflow_runs(
        workflow_id=workflow_id,
        window_hours=effective_window,
    )

    # Filter to retriable conclusions (attempt-cap check happens after selecting the oldest run)
    eligible = [r for r in runs if r.conclusion in RETRIABLE_CONCLUSIONS]

    if not eligible:
        logger.info("No eligible runs found for reconciliation")
        return ReconciliationResult(
            action=ReconciliationAction.NO_ACTION,
            message="No retriable runs found within the configured window.",
        )

    # Sort by created_at ascending → oldest first (single run per invocation).
    # Missing or invalid timestamps are treated as newest so they do not take
    # priority over runs with valid, comparable creation times.
    eligible.sort(key=lambda r: _parse_created_at_for_sort(r.created_at))
    retry_candidate = next(
        (run for run in eligible if run.run_attempt < effective_max_attempts),
        None,
    )
    # When all runs are maxed out, we escalate the oldest one for deterministic reporting.
    selected = retry_candidate or eligible[0]

    # Resolve context for status reporting
    context: RunEventContext | None = None
    try:
        context = map_run_context(selected)
    except UnmappableContextError as exc:
        logger.warning("Could not map run context: %s", exc)

    # If no run is still under the retry cap, escalate the oldest maxed run.
    if retry_candidate is None:
        logger.warning(
            "Run %d has reached max attempts (%d/%d) — escalating",
            selected.id,
            selected.run_attempt,
            effective_max_attempts,
        )
        comment_posted = _post_escalation(provider, selected, context)
        escalation_note = (
            "Escalation comment posted."
            if comment_posted
            else "Escalation comment not posted (no pull-request target or post failed)."
        )
        return ReconciliationResult(
            action=ReconciliationAction.ESCALATED,
            run=selected,
            message=(
                f"Run {selected.id} ({selected.conclusion}) reached max attempts "
                f"({selected.run_attempt}/{effective_max_attempts}). {escalation_note}"
            ),
            context=context,
        )

    # Retry the oldest run that is still under the retry cap.
    logger.info(
        "Retrying run %d (attempt %d/%d, conclusion=%s)",
        selected.id,
        selected.run_attempt,
        effective_max_attempts,
        selected.conclusion,
    )
    provider.rerun_workflow(selected.id)

    return ReconciliationResult(
        action=ReconciliationAction.RETRIED,
        run=selected,
        message=(
            "Retried run "
            f"{selected.id} ({selected.conclusion}, attempt "
            f"{selected.run_attempt}/{effective_max_attempts})."
        ),
        context=context,
    )


def _post_escalation(
    provider: CIPlatformProvider,
    run: WorkflowRun,
    context: RunEventContext | None,
) -> bool:
    """Post an escalation comment to the appropriate target.

    Uses the provider's post_comment method when the context resolves to
    a pull request. For non-PR contexts, logs a warning since there is no
    supported comment target on the provider interface.

    Returns:
        True if the comment was successfully posted, False otherwise.
    """
    run_ref = f"[{run.name} #{run.id}]({run.html_url})" if run.html_url else f"{run.name} #{run.id}"
    body = (
        f"⚠️ **Reconciliation Escalation**\n\n"
        f"Workflow run {run_ref} has failed "
        f"{run.run_attempt} time(s) with conclusion `{run.conclusion}` "
        f"and reached the maximum retry limit.\n\n"
        f"Manual investigation required."
    )

    if context and context.target_type == "pull_request" and context.target_id:
        try:
            provider.post_comment(context.target_id, body)
            logger.info("Escalation posted to %s #%d", context.target_type, context.target_id)
            return True
        except Exception as exc:
            logger.error("Failed to post escalation comment: %s", exc)
            return False
    else:
        logger.warning(
            "Cannot post escalation: no pull_request target (context=%s)",
            context,
        )
        return False


def _parse_created_at_for_sort(created_at: str) -> datetime:
    """Parse provider timestamps for deterministic oldest-first ordering.

    Empty or invalid timestamps return ``datetime.max`` so they sort last and
    cannot preempt runs with valid creation times. Naive timestamps are treated
    as UTC for stable cross-provider comparisons.
    """
    if not created_at:
        return datetime.max.replace(tzinfo=timezone.utc)

    normalized = created_at.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.max.replace(tzinfo=timezone.utc)

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)
