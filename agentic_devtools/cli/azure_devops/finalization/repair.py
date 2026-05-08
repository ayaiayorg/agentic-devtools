"""Batch-first and targeted fallback repair for non-converged comments."""

from __future__ import annotations

import sys
from typing import Any

from ..config import AzureDevOpsConfig
from ..marker import build_marker
from ..review_state import COMPLETE_STATUSES, ReviewState, ReviewStatus
from .convergence import compute_expected_content
from .models import BatchRepairResult, EligibleComment, EligibleComments, TargetedRepairResult


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
    (approved/needs-work).  Calls ``_complete_active_session()`` for
    activity-log finalization.

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

    # Ensure all files have terminal statuses in review state
    for file_path, file_entry in review_state.files.items():
        if file_entry.status not in COMPLETE_STATUSES:
            file_entry.status = ReviewStatus.APPROVED.value

    # Repair file summaries via direct PATCH (re-render from state)
    for comment in eligible.file_summaries:
        result.attempted += 1
        if dry_run:
            result.succeeded += 1
            continue

        try:
            expected = compute_expected_content(comment, review_state, base_url)
            marker = build_marker(
                "file-summary",
                file=comment.file_path,
                pr=pr_id,
            )
            new_content = f"{marker}\n{expected}"
            _patch_comment(config, headers, review_state.repoId, pr_id, comment, new_content)
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
                _complete_activity_log(pr_id)
                result.activity_log_completed = True
            except (Exception, SystemExit) as exc:
                result.errors.append(f"activity-log completion: {exc}")

    return result


def targeted_repair(
    non_converged: list[EligibleComment],
    expected_map: dict[int, str],
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
        expected_map: Map of comment_id → expected body content.
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

        expected = expected_map.get(comment.comment_id, "")
        if not expected:
            result.failed += 1
            result.errors.append(f"No expected content for comment {comment.comment_id}")
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
                _patch_comment(config, headers, review_state.repoId, pr_id, comment, new_content)
            result.succeeded += 1
        except Exception as exc:
            result.failed += 1
            result.errors.append(f"{comment.marker_type} thread={comment.thread_id}: {exc}")

    return result


def _patch_comment(
    config: AzureDevOpsConfig,
    headers: dict[str, str],
    repo_id: str,
    pr_id: int,
    comment: EligibleComment,
    new_content: str,
) -> None:
    """PATCH a single comment's content via Azure DevOps API."""
    from ..helpers import require_requests

    requests_module: Any = require_requests()
    url = config.build_api_url(
        repo_id,
        "pullRequests",
        pr_id,
        "threads",
        comment.thread_id,
        "comments",
        comment.comment_id,
    )
    payload = {"content": new_content}
    response = requests_module.patch(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()


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


def _complete_activity_log(pr_id: int) -> None:
    """Complete the active review session's activity log."""
    try:
        from ..file_review_commands import _complete_active_session

        _complete_active_session(pr_id)
    except SystemExit:
        # _complete_active_session may call sys.exit; treat as non-blocking
        print("Warning: _complete_active_session raised SystemExit", file=sys.stderr)


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
