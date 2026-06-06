"""Post-agent evaluator action handlers.

Each function handles a specific classification scenario, performing the
appropriate remediation via the provider abstraction.
"""

from __future__ import annotations

import logging
from typing import Protocol

from ..guards import THREAD_EVALUATED_MARKER
from ..models import COPILOT_COMMENT_LOGINS, COPILOT_REVIEWER_LOGIN
from ..provider import CIPlatformProvider
from .diff_heuristic import check_lines_modified
from .models import (
    EvaluationResult,
    PostAgentAction,
    PostAgentClassification,
    PostAgentSnapshot,
)

logger = logging.getLogger(__name__)

_SENTINEL_MARKER = "<!-- copilot-agent-result -->"
_COPILOT_REVIEWER = COPILOT_REVIEWER_LOGIN


class _ActionHandler(Protocol):
    """Callable interface for evaluator action handlers."""

    def __call__(  # pragma: no branch
        self,
        provider: CIPlatformProvider,
        snapshot: PostAgentSnapshot,
        *,
        dry_run: bool = False,
    ) -> EvaluationResult: ...


def _get_evaluated_thread_ids(
    provider: CIPlatformProvider,
    snapshot: PostAgentSnapshot,
) -> set[int] | None:
    """Return root thread comment IDs with authorized thread-evaluated marker replies."""
    review_id = snapshot.review_id or snapshot.repair_satisfied_review_id
    if not review_id:
        return None
    try:
        review_comments = provider.list_review_comments(snapshot.pr_number, review_id)
    except Exception as exc:
        logger.warning("Failed to fetch review comments for marker resolution: %s", exc)
        return None

    parent_by_id: dict[int, int | None] = {comment.id: comment.in_reply_to_id for comment in review_comments}

    def _resolve_root_comment_id(comment_id: int) -> int | None:
        current_id = comment_id
        visited: set[int] = set()
        while True:
            if current_id in visited:
                return None
            visited.add(current_id)
            parent_id = parent_by_id.get(current_id)
            if parent_id is None:
                return current_id
            if parent_id <= 0:
                return None
            if parent_id not in parent_by_id:
                return parent_id
            current_id = parent_id

    # Group all comments by their root thread
    thread_comments: dict[int, list] = {}
    for comment in review_comments:
        root_id = _resolve_root_comment_id(comment.id)
        if root_id is not None and root_id > 0:
            thread_comments.setdefault(root_id, []).append(comment)

    # A thread is evaluated only when the most-recent comment (highest ID) in
    # that thread carries the marker *and* is authored by an authorized identity.
    # This prevents a Copilot marker from being treated as active when a human
    # has replied to the thread after it.
    evaluated_thread_ids: set[int] = set()
    for root_id, comments in thread_comments.items():
        latest = max(comments, key=lambda c: c.id)
        if THREAD_EVALUATED_MARKER in latest.body and latest.author_login in COPILOT_COMMENT_LOGINS:
            evaluated_thread_ids.add(root_id)
    return evaluated_thread_ids


def no_action(
    provider: CIPlatformProvider,
    snapshot: PostAgentSnapshot,
    *,
    classification: PostAgentClassification | None = None,
    dry_run: bool = False,
) -> EvaluationResult:
    """Handle complete or concurrent-skipped states — no remediation needed."""
    unresolved = [t for t in snapshot.threads if not t.is_resolved]
    return EvaluationResult(
        classification=classification
        or (
            PostAgentClassification.complete
            if snapshot.has_sentinel
            else PostAgentClassification.concurrent_evaluation_skipped
        ),
        action_taken=PostAgentAction.no_action,
        success=True,
        threads_resolved=0,
        threads_unresolved=len(unresolved),
        dry_run=dry_run,
    )


def verify_and_resolve(
    provider: CIPlatformProvider,
    snapshot: PostAgentSnapshot,
    *,
    dry_run: bool = False,
) -> EvaluationResult:
    """Verify threads against diff and resolve verified ones.

    Used when the agent claims fixes are already done but threads remain
    unresolved. Checks which threads target lines that were modified, then
    resolves them programmatically.
    """
    unresolved = [t for t in snapshot.threads if not t.is_resolved]
    if not dry_run and not snapshot.head_changed_since_review:
        return EvaluationResult(
            classification=PostAgentClassification.agent_claims_fixed_no_sentinel,
            action_taken=PostAgentAction.verify_and_resolve,
            success=False,
            threads_resolved=0,
            threads_unresolved=len(unresolved),
            error_details="No post-review code changes to verify against",
            dry_run=False,
        )

    verified_ids: list[int] = []
    unverified_count = 0

    for thread in unresolved:
        if thread.path and snapshot.diff_text:
            modified = check_lines_modified(
                snapshot.diff_text,
                thread.path,
                thread.start_line,
                thread.end_line,
            )
            if modified:
                verified_ids.append(thread.comment_id)
            else:
                unverified_count += 1
        else:
            # PR-level comments or no diff — cannot verify
            unverified_count += 1

    if dry_run:
        return EvaluationResult(
            classification=PostAgentClassification.agent_claims_fixed_no_sentinel,
            action_taken=PostAgentAction.verify_and_resolve,
            success=True,
            threads_resolved=len(verified_ids),
            threads_unresolved=unverified_count,
            dry_run=True,
        )

    # Resolve verified threads
    resolved_count = 0
    resolution_failed_count = 0
    if verified_ids:
        try:
            from ...github.resolve_review_threads import resolve_review_threads

            resolution_result = resolve_review_threads(
                pr_number=snapshot.pr_number,
                repo=snapshot.repo,
                comment_ids=verified_ids,
            )
            resolved_count = int(resolution_result.get("threadsResolved", 0)) + int(
                resolution_result.get("alreadyResolved", 0)
            )
            resolution_failed_count = int(resolution_result.get("threadsFailed", 0))
            if not bool(resolution_result.get("verified", False)):
                return EvaluationResult(
                    classification=PostAgentClassification.agent_claims_fixed_no_sentinel,
                    action_taken=PostAgentAction.verify_and_resolve,
                    success=False,
                    threads_resolved=resolved_count,
                    threads_unresolved=unverified_count + resolution_failed_count,
                    error_details="Thread resolution verification failed",
                    dry_run=False,
                )
            # Even with verified=True, totalTargeted may be 0 or less than the
            # number of IDs requested (e.g. when comment IDs could not be mapped
            # to review threads).  Ensure every requested ID was accounted for.
            if resolved_count < len(verified_ids):
                shortfall = len(verified_ids) - resolved_count
                return EvaluationResult(
                    classification=PostAgentClassification.agent_claims_fixed_no_sentinel,
                    action_taken=PostAgentAction.verify_and_resolve,
                    success=False,
                    threads_resolved=resolved_count,
                    threads_unresolved=unverified_count + shortfall,
                    error_details="Resolved count does not cover all verified thread IDs",
                    dry_run=False,
                )
        except Exception as exc:
            logger.warning("Failed to resolve threads: %s", exc)
            return EvaluationResult(
                classification=PostAgentClassification.agent_claims_fixed_no_sentinel,
                action_taken=PostAgentAction.verify_and_resolve,
                success=False,
                threads_resolved=0,
                threads_unresolved=len(unresolved),
                error_details=str(exc),
                dry_run=False,
            )

    if unverified_count > 0:
        return EvaluationResult(
            classification=PostAgentClassification.agent_claims_fixed_no_sentinel,
            action_taken=PostAgentAction.verify_and_resolve,
            success=False,
            threads_resolved=resolved_count,
            threads_unresolved=unverified_count + resolution_failed_count,
            error_details="Unverified unresolved threads remain",
            dry_run=False,
        )

    # Post sentinel comment
    try:
        sentinel_body = (
            f"{_SENTINEL_MARKER}\n"
            f"**Post-Agent Evaluator**: Verified and resolved "
            f"{resolved_count}/{len(unresolved)} threads. "
            f"HEAD: `{snapshot.current_head_sha[:8]}`."
        )
        provider.post_comment(snapshot.pr_number, sentinel_body)
    except Exception as exc:
        logger.warning("Failed to post sentinel: %s", exc)

    return EvaluationResult(
        classification=PostAgentClassification.agent_claims_fixed_no_sentinel,
        action_taken=PostAgentAction.verify_and_resolve,
        success=True,
        threads_resolved=resolved_count,
        threads_unresolved=unverified_count + resolution_failed_count,
        dry_run=False,
    )


def synthesize_sentinel(
    provider: CIPlatformProvider,
    snapshot: PostAgentSnapshot,
    *,
    dry_run: bool = False,
) -> EvaluationResult:
    """Synthesize a sentinel comment when agent pushed code but didn't post one.

    Used when code changes were made but no structured result was posted.
    """
    unresolved = [t for t in snapshot.threads if not t.is_resolved]

    if dry_run:
        return EvaluationResult(
            classification=PostAgentClassification.threads_resolved_no_sentinel,
            action_taken=PostAgentAction.synthesize_sentinel,
            success=True,
            threads_resolved=0,
            threads_unresolved=len(unresolved),
            dry_run=True,
        )

    try:
        sentinel_body = (
            f"{_SENTINEL_MARKER}\n"
            f"**Post-Agent Evaluator**: Synthesized result summary. "
            f"HEAD: `{snapshot.current_head_sha[:8]}`. "
            f"Threads remaining: {len(unresolved)}."
        )
        provider.post_comment(snapshot.pr_number, sentinel_body)
    except Exception as exc:
        return EvaluationResult(
            classification=PostAgentClassification.threads_resolved_no_sentinel,
            action_taken=PostAgentAction.synthesize_sentinel,
            success=False,
            threads_resolved=0,
            threads_unresolved=len(unresolved),
            error_details=str(exc),
            dry_run=False,
        )

    return EvaluationResult(
        classification=PostAgentClassification.threads_resolved_no_sentinel,
        action_taken=PostAgentAction.synthesize_sentinel,
        success=True,
        threads_resolved=0,
        threads_unresolved=len(unresolved),
        dry_run=False,
    )


def trigger_re_review(
    provider: CIPlatformProvider,
    snapshot: PostAgentSnapshot,
    *,
    classification: PostAgentClassification | None = None,
    dry_run: bool = False,
) -> EvaluationResult:
    """Trigger a Copilot re-review when changes were made but threads unresolved.

    Args:
        provider: CI platform provider.
        snapshot: PR state snapshot.
        classification: Classification to report in the result.  Defaults to
            ``changes_made_threads_unresolved`` when not provided, but callers
            routing from a different classification (e.g.
            ``agent_claims_fixed_no_sentinel``) should pass the original value
            so the result faithfully reflects the actual classification.
        dry_run: If True, preview without executing side effects.
    """
    effective_classification = classification or PostAgentClassification.changes_made_threads_unresolved
    unresolved = [t for t in snapshot.threads if not t.is_resolved]

    if dry_run:
        return EvaluationResult(
            classification=effective_classification,
            action_taken=PostAgentAction.trigger_re_review,
            success=True,
            threads_resolved=0,
            threads_unresolved=len(unresolved),
            dry_run=True,
        )

    try:
        provider.request_reviewer(snapshot.pr_number, _COPILOT_REVIEWER)
    except Exception as exc:
        return EvaluationResult(
            classification=effective_classification,
            action_taken=PostAgentAction.trigger_re_review,
            success=False,
            threads_resolved=0,
            threads_unresolved=len(unresolved),
            error_details=str(exc),
            dry_run=False,
        )

    return EvaluationResult(
        classification=effective_classification,
        action_taken=PostAgentAction.trigger_re_review,
        success=True,
        threads_resolved=0,
        threads_unresolved=len(unresolved),
        dry_run=False,
    )


def agentic_fallback(
    provider: CIPlatformProvider,
    snapshot: PostAgentSnapshot,
    *,
    dry_run: bool = False,
) -> EvaluationResult:
    """Dispatch an agentic repair session as a last resort."""
    unresolved = [t for t in snapshot.threads if not t.is_resolved]

    if dry_run:
        return EvaluationResult(
            classification=PostAgentClassification.agent_silent,
            action_taken=PostAgentAction.agentic_fallback,
            success=True,
            threads_resolved=0,
            threads_unresolved=len(unresolved),
            dry_run=True,
        )

    try:
        provider.dispatch_repair(
            pr_number=snapshot.pr_number,
            head_sha=snapshot.current_head_sha,
            repair_type="review",
            failed_checks=[],
            review_comments=[],
            review_id=snapshot.review_id,
        )
    except Exception as exc:
        return EvaluationResult(
            classification=PostAgentClassification.agent_silent,
            action_taken=PostAgentAction.agentic_fallback,
            success=False,
            threads_resolved=0,
            threads_unresolved=len(unresolved),
            error_details=str(exc),
            dry_run=False,
        )

    return EvaluationResult(
        classification=PostAgentClassification.agent_silent,
        action_taken=PostAgentAction.agentic_fallback,
        success=True,
        threads_resolved=0,
        threads_unresolved=len(unresolved),
        dry_run=False,
    )


def resolve_evaluated_threads(
    provider: CIPlatformProvider,
    snapshot: PostAgentSnapshot,
    *,
    dry_run: bool = False,
) -> EvaluationResult:
    """Resolve threads that have been individually evaluated by the agent.

    Used when the agent determines no code changes are needed and posts
    the repair-satisfied marker. Resolves threads that have a
    thread-evaluated reply from an authorized Copilot identity.

    Validates review-id match before resolving (FR-011).
    """
    unresolved = [t for t in snapshot.threads if not t.is_resolved]

    if not unresolved:
        # snapshot.threads may be empty because _load_review_threads() swallowed
        # an exception.  Confirm via the provider before declaring success.
        try:
            live_count = provider.count_unresolved_review_threads(snapshot.pr_number)
        except Exception as exc:
            logger.warning(
                "PR #%d: could not verify unresolved thread count: %s — failing closed",
                snapshot.pr_number,
                exc,
            )
            return EvaluationResult(
                classification=PostAgentClassification.repair_satisfied_no_changes,
                action_taken=PostAgentAction.resolve_evaluated_threads,
                success=False,
                threads_resolved=0,
                threads_unresolved=0,
                error_details="could not verify unresolved thread count",
                dry_run=dry_run,
            )
        if live_count > 0:
            logger.warning(
                "PR #%d: snapshot has no unresolved threads but provider reports %d — thread load may have failed",
                snapshot.pr_number,
                live_count,
            )
            return EvaluationResult(
                classification=PostAgentClassification.repair_satisfied_no_changes,
                action_taken=PostAgentAction.resolve_evaluated_threads,
                success=False,
                threads_resolved=0,
                threads_unresolved=live_count,
                error_details="snapshot thread load failed — unresolved threads detected",
                dry_run=dry_run,
            )
        return EvaluationResult(
            classification=PostAgentClassification.repair_satisfied_no_changes,
            action_taken=PostAgentAction.resolve_evaluated_threads,
            success=True,
            threads_resolved=0,
            threads_unresolved=0,
            dry_run=dry_run,
        )

    # Validate review-id match
    if (
        snapshot.repair_satisfied_review_id is not None
        and snapshot.review_id
        and snapshot.repair_satisfied_review_id != snapshot.review_id
    ):
        logger.warning(
            "PR #%d: repair-satisfied review-id %d does not match active review %d — ignoring",
            snapshot.pr_number,
            snapshot.repair_satisfied_review_id,
            snapshot.review_id,
        )
        return EvaluationResult(
            classification=PostAgentClassification.repair_satisfied_no_changes,
            action_taken=PostAgentAction.resolve_evaluated_threads,
            success=False,
            threads_resolved=0,
            threads_unresolved=len(unresolved),
            error_details="review-id mismatch",
            dry_run=dry_run,
        )

    evaluated_thread_ids = _get_evaluated_thread_ids(provider, snapshot)
    if evaluated_thread_ids is None:
        return EvaluationResult(
            classification=PostAgentClassification.repair_satisfied_no_changes,
            action_taken=PostAgentAction.resolve_evaluated_threads,
            success=False,
            threads_resolved=0,
            threads_unresolved=len(unresolved),
            error_details="thread marker signals unavailable",
            dry_run=dry_run,
        )

    # Identify threads with thread-evaluated markers from authorized identities
    threads_to_resolve: list[int] = []
    threads_missing_marker: list[int] = []

    for thread in unresolved:
        has_marker = thread.comment_id in evaluated_thread_ids
        if has_marker:
            threads_to_resolve.append(thread.comment_id)
        else:
            threads_missing_marker.append(thread.comment_id)

    if threads_missing_marker:
        logger.warning(
            "PR #%d: %d threads lack thread-evaluated reply — partial resolution",
            snapshot.pr_number,
            len(threads_missing_marker),
        )

    if dry_run:
        return EvaluationResult(
            classification=PostAgentClassification.repair_satisfied_no_changes,
            action_taken=PostAgentAction.resolve_evaluated_threads,
            success=True,
            threads_resolved=len(threads_to_resolve),
            threads_unresolved=len(threads_missing_marker),
            dry_run=True,
        )

    # Resolve threads
    resolved_count = 0
    resolution_failed_count = 0
    if threads_to_resolve:
        try:
            from ...github.resolve_review_threads import resolve_review_threads

            resolution_result = resolve_review_threads(
                pr_number=snapshot.pr_number,
                repo=snapshot.repo,
                comment_ids=threads_to_resolve,
            )
            resolved_count = int(resolution_result.get("threadsResolved", 0)) + int(
                resolution_result.get("alreadyResolved", 0)
            )
            resolution_failed_count = int(resolution_result.get("threadsFailed", 0))
            if not bool(resolution_result.get("verified", False)):
                return EvaluationResult(
                    classification=PostAgentClassification.repair_satisfied_no_changes,
                    action_taken=PostAgentAction.resolve_evaluated_threads,
                    success=False,
                    threads_resolved=resolved_count,
                    threads_unresolved=len(threads_missing_marker) + resolution_failed_count,
                    error_details="Thread resolution verification failed",
                    dry_run=False,
                )
            if resolved_count < len(threads_to_resolve):
                shortfall = len(threads_to_resolve) - resolved_count
                return EvaluationResult(
                    classification=PostAgentClassification.repair_satisfied_no_changes,
                    action_taken=PostAgentAction.resolve_evaluated_threads,
                    success=False,
                    threads_resolved=resolved_count,
                    threads_unresolved=len(threads_missing_marker) + shortfall,
                    error_details="Resolved count does not cover all targeted thread IDs",
                    dry_run=False,
                )
        except Exception as exc:
            logger.warning("Failed to resolve evaluated threads: %s", exc)
            return EvaluationResult(
                classification=PostAgentClassification.repair_satisfied_no_changes,
                action_taken=PostAgentAction.resolve_evaluated_threads,
                success=False,
                threads_resolved=0,
                threads_unresolved=len(unresolved),
                error_details=str(exc),
                dry_run=False,
            )

    effective_review_id = snapshot.review_id or snapshot.repair_satisfied_review_id or 0
    logger.info(
        "PR #%d: repair_satisfied detected — review_id=%d, "
        "threads_evaluated=%d, threads_resolved=%d, threads_missing=%d, "
        "outcome=agent_no_changes_needed",
        snapshot.pr_number,
        effective_review_id,
        len(threads_to_resolve),
        resolved_count,
        len(threads_missing_marker),
    )

    if threads_missing_marker:
        return EvaluationResult(
            classification=PostAgentClassification.repair_satisfied_no_changes,
            action_taken=PostAgentAction.resolve_evaluated_threads,
            success=False,
            threads_resolved=resolved_count,
            threads_unresolved=len(threads_missing_marker) + resolution_failed_count,
            error_details="Unmarked unresolved threads remain",
            dry_run=False,
        )

    return EvaluationResult(
        classification=PostAgentClassification.repair_satisfied_no_changes,
        action_taken=PostAgentAction.resolve_evaluated_threads,
        success=True,
        threads_resolved=resolved_count,
        threads_unresolved=len(threads_missing_marker),
        dry_run=False,
    )


# Action dispatch map: classification → handler function
ACTION_DISPATCH: dict[
    PostAgentClassification,
    _ActionHandler,
] = {
    PostAgentClassification.complete: no_action,
    PostAgentClassification.concurrent_evaluation_skipped: no_action,
    PostAgentClassification.repair_satisfied_no_changes: resolve_evaluated_threads,
    PostAgentClassification.agent_claims_fixed_no_sentinel: trigger_re_review,
    PostAgentClassification.threads_resolved_no_sentinel: synthesize_sentinel,
    PostAgentClassification.changes_made_threads_unresolved: trigger_re_review,
    PostAgentClassification.agent_silent: agentic_fallback,
}


def dispatch_action(
    classification: PostAgentClassification,
    provider: CIPlatformProvider,
    snapshot: PostAgentSnapshot,
    *,
    dry_run: bool = False,
) -> EvaluationResult:
    """Dispatch the appropriate action handler for a classification.

    Args:
        classification: The determined classification.
        provider: CI platform provider.
        snapshot: PR state snapshot.
        dry_run: If True, preview without executing side effects.

    Returns:
        EvaluationResult from the handler.
    """
    handler = ACTION_DISPATCH[classification]
    if handler is no_action:
        return no_action(
            provider,
            snapshot,
            classification=classification,
            dry_run=dry_run,
        )
    if classification == PostAgentClassification.agent_claims_fixed_no_sentinel:
        if snapshot.head_changed_since_review:
            return verify_and_resolve(provider, snapshot, dry_run=dry_run)
        # No post-review changes: trigger re-review but preserve the original classification.
        return trigger_re_review(
            provider,
            snapshot,
            classification=classification,
            dry_run=dry_run,
        )
    return handler(provider, snapshot, dry_run=dry_run)
