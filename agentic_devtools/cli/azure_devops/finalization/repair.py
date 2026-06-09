"""Batch-first and targeted fallback repair for non-converged comments."""

from __future__ import annotations

from datetime import datetime, timezone

from ..config import AzureDevOpsConfig
from ..helpers import patch_comment, patch_thread_status, require_requests
from ..marker import build_marker
from ..review_state import ReviewState, normalize_file_path
from ..status_cascade import _THREAD_STATUS_MAP
from .convergence import check_convergence, compute_expected_content
from .models import BatchRepairResult, CommentKey, EligibleComment, EligibleComments, TargetedRepairResult, comment_key


def batch_repair_pass(
    eligible: EligibleComments,
    review_state: ReviewState,
    config: AzureDevOpsConfig,
    headers: dict[str, str],
    pr_id: int,
    base_url: str,
    dry_run: bool = False,
) -> BatchRepairResult:
    """Perform batch repair of non-converged file summaries and cascade.

    Drives file-summary convergence by re-rendering from review state and
    executing a single cascade at the end.  Preserves existing file verdicts
    (approved/needs-work).  Completes the active review session directly on
    the already-loaded *review_state* for activity-log finalization.

    Args:
        eligible: Classified eligible comments.
        review_state: Current review state (source of truth).
        config: Azure DevOps configuration.
        headers: Auth headers for API calls.
        pr_id: Pull request ID.
        base_url: PR root URL for rendering.
        dry_run: If True, skip all mutations.

    Returns:
        BatchRepairResult with counts and errors.
    """
    result = BatchRepairResult()

    # Repair file summaries via direct PATCH (re-render from state)
    for comment in eligible.file_summaries:
        result.attempted += 1
        if dry_run:
            result.succeeded += 1
            continue

        try:
            expected = compute_expected_content(comment, review_state, base_url)
            if not expected:
                result.failed += 1
                result.errors.append(
                    f"file-summary {comment.file_path}: empty expected content, skipping to avoid wiping comment"
                )
                continue
            # Skip PATCH if already converged to avoid unnecessary API calls
            if check_convergence(comment, expected):
                result.succeeded += 1
                continue
            marker = build_marker(
                "file-summary",
                file=comment.file_path,
                pr=pr_id,
            )
            new_content = f"{marker}\n{expected}"
            requests_module = require_requests()
            patch_comment(
                requests_module,
                headers,
                config,
                review_state.repoId,
                pr_id,
                comment.thread_id,
                comment.comment_id,
                new_content,
                reply_on_forbidden=True,
            )
            # Sync thread status with file review status
            _patch_file_thread_status(
                comment,
                review_state,
                config,
                headers,
                pr_id,
            )
            result.succeeded += 1
        except Exception as exc:
            result.failed += 1
            result.errors.append(f"file-summary {comment.file_path}: {exc}")

    # Repair overall summary via cascade
    if eligible.overall_summary is not None:
        result.attempted += 1
        if dry_run:
            result.succeeded += 1
        else:
            try:
                _cascade_overall_summary(review_state, config, headers, pr_id, base_url)
                result.succeeded += 1
            except Exception as exc:
                result.failed += 1
                result.errors.append(f"overall-summary: {exc}")

    # Complete activity log session
    if eligible.activity_log_entries:
        if dry_run:
            result.activity_log_completed = True
        else:
            try:
                _complete_activity_log(review_state, config, headers, pr_id)
                result.activity_log_completed = True
            except Exception as exc:
                result.errors.append(f"activity-log completion: {exc}")

    return result


def targeted_repair(
    non_converged: list[EligibleComment],
    expected_map: dict[CommentKey, str],
    config: AzureDevOpsConfig,
    headers: dict[str, str],
    pr_id: int,
    review_state: ReviewState,
    dry_run: bool = False,
) -> TargetedRepairResult:
    """Repair individual non-converged comments via direct PATCH.

    Only targets comments that remain non-converged after the batch pass.
    Content is rendered from authoritative review state, with the marker
    prepended before PATCH.

    Activity-log entries use ``_update_activity_log_comment_status()``
    for targeted repair.

    Args:
        non_converged: List of non-converged comments.
        expected_map: Map of (thread_id, comment_id) → expected body content.
        config: Azure DevOps configuration.
        headers: Auth headers for API calls.
        pr_id: Pull request ID.
        review_state: Current review state.
        dry_run: If True, skip all mutations.

    Returns:
        TargetedRepairResult with counts and errors.
    """
    result = TargetedRepairResult()

    for comment in non_converged:
        result.attempted += 1
        if dry_run:
            result.succeeded += 1
            continue

        expected = expected_map.get(comment_key(comment), "")
        if not expected:
            result.failed += 1
            result.errors.append(
                f"No expected content for comment thread={comment.thread_id} comment={comment.comment_id}"
            )
            continue

        try:
            if comment.marker_type == "activity-log-entry":
                _targeted_repair_activity_log(comment, review_state, config, headers, pr_id)
            else:
                marker = build_marker(
                    comment.marker_type,
                    file=comment.file_path,
                    pr=pr_id,
                )
                new_content = f"{marker}\n{expected}"
                requests_module = require_requests()
                patch_comment(
                    requests_module,
                    headers,
                    config,
                    review_state.repoId,
                    pr_id,
                    comment.thread_id,
                    comment.comment_id,
                    new_content,
                    reply_on_forbidden=True,
                )
                # Sync thread status for file-summary comments
                if comment.marker_type == "file-summary":
                    _patch_file_thread_status(
                        comment,
                        review_state,
                        config,
                        headers,
                        pr_id,
                    )
            result.succeeded += 1
        except Exception as exc:
            result.failed += 1
            result.errors.append(f"{comment.marker_type} thread={comment.thread_id}: {exc}")

    return result


def _cascade_overall_summary(
    review_state: ReviewState,
    config: AzureDevOpsConfig,
    headers: dict[str, str],
    pr_id: int,
    base_url: str,
) -> None:
    """Re-cascade the overall summary from current review state."""
    from ..helpers import require_requests as _require_requests
    from ..status_cascade import cascade_overall_summary_update, execute_cascade

    patch_ops = cascade_overall_summary_update(review_state, base_url)
    requests_mod = _require_requests()
    execute_cascade(
        patch_operations=patch_ops,
        requests_module=requests_mod,
        headers=headers,
        config=config,
        repo_id=review_state.repoId,
        pull_request_id=pr_id,
    )


def _complete_activity_log(
    review_state: ReviewState,
    config: AzureDevOpsConfig,
    headers: dict[str, str],
    pr_id: int,
) -> None:
    """Complete the active review session's activity log.

    Operates on the already-loaded *review_state* to avoid a redundant
    load-mutate-save cycle that would race with the caller's copy.

    Args:
        review_state: The already-loaded review state (mutated in place).
        config: Azure DevOps configuration.
        headers: Auth headers for API calls.
        pr_id: Pull request ID.
    """
    completed_session = None

    for session in reversed(review_state.sessions):
        if session.status == "in_progress":
            session.status = "completed"
            session.completedUtc = datetime.now(timezone.utc).isoformat()
            completed_session = session
            break

    if completed_session is None:
        return

    if completed_session.activityLogCommentId is not None and review_state.activityLogThreadId:
        from ..review_scaffold import _update_activity_log_comment_status

        requests_module = require_requests()
        threads_url = config.build_api_url(
            review_state.repoId,
            "pullRequests",
            pr_id,
            "threads",
        )
        session_index = review_state.sessions.index(completed_session) + 1

        _update_activity_log_comment_status(
            requests_module,
            headers,
            threads_url,
            review_state.activityLogThreadId,
            completed_session.activityLogCommentId,
            "✅",
            "Completed",
            completed_session,
            review_state.commitHash or "unknown",
            session_index,
            "Review session completed successfully.",
        )


def _targeted_repair_activity_log(
    comment: EligibleComment,
    review_state: ReviewState,
    config: AzureDevOpsConfig,
    headers: dict[str, str],
    pr_id: int,
) -> None:
    """Repair an activity-log entry via _update_activity_log_comment_status."""
    from ..helpers import require_requests
    from ..review_scaffold import _update_activity_log_comment_status

    if not review_state.sessions:
        return

    session = review_state.sessions[-1]
    commit_hash = review_state.commitHash or "unknown"
    session_index = len(review_state.sessions)

    requests_module = require_requests()
    threads_url = config.build_api_url(review_state.repoId, "pullRequests", pr_id, "threads")

    _update_activity_log_comment_status(
        requests_module,
        headers,
        threads_url,
        comment.thread_id,
        comment.comment_id,
        "✅",
        "Completed",
        session,
        commit_hash,
        session_index,
        "Review session completed successfully.",
    )


def _patch_file_thread_status(
    comment: EligibleComment,
    review_state: ReviewState,
    config: AzureDevOpsConfig,
    headers: dict[str, str],
    pr_id: int,
) -> None:
    """Patch the thread status to match the file's review status.

    Mirrors the behaviour of ``approve_file`` / ``execute_cascade`` which
    always keep thread status in sync with the review verdict (e.g.
    ``approved`` → ``closed``, ``needs-work`` → ``active``).

    Args:
        comment: The file-summary comment being repaired.
        review_state: Current review state (source of truth for file status).
        config: Azure DevOps configuration.
        headers: Auth headers for API calls.
        pr_id: Pull request ID.
    """
    if not comment.file_path:
        return

    normalized = normalize_file_path(comment.file_path)
    file_entry = review_state.files.get(normalized)
    if file_entry is None:
        return

    thread_status = _THREAD_STATUS_MAP.get(file_entry.status, "active")
    requests_module = require_requests()
    patch_thread_status(
        requests_module,
        headers,
        config,
        review_state.repoId,
        pr_id,
        comment.thread_id,
        thread_status,
    )
