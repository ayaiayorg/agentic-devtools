"""AI PR loop orchestrator.

State machine extracted from ai-pr-loop.yml. Implements:
metadata resolution → guards → CI status check → review evaluation →
repair dispatch → approval → merge.

When actionable Copilot review comments or failing CI checks are detected,
the orchestrator dispatches a repair by posting a @copilot-tagged comment
on the PR (FR-001, FR-002).  A Copilot review is considered actionable when
its state is CHANGES_REQUESTED, or COMMENTED with inline comments.  When
everything is green, it approves and merges.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

from agentic_devtools.cli.ci.guards import (
    LABEL_NO_AUTO_MERGE,
    LABEL_SKIP_ENTIRELY,
    PRIVILEGED_PREFIXES,
    check_cycle_limit,
    check_deduplication,
    check_docker_files,
    check_exclusion_labels,
    check_fork_pr,
    check_privileged_paths,
    increment_cycle_count,
)
from agentic_devtools.cli.ci.models import (
    COPILOT_COMMENT_LOGINS,
    COPILOT_LOGINS,
    COPILOT_REVIEWER_LOGIN,
    CheckRunStatus,
    EventPayload,
    PRMetadata,
    RepairDecision,
    ReviewCommentInfo,
    ReviewInfo,
)
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)


def _is_github_actions() -> bool:
    """Return True when running inside GitHub Actions."""
    return os.environ.get("GITHUB_ACTIONS") == "true"


def _log_group(title: str) -> None:
    """Emit a ``::group::`` annotation when running in GitHub Actions."""
    if _is_github_actions():
        print(f"::group::{title}", file=sys.stderr, flush=True)


def _log_endgroup() -> None:
    """Emit an ``::endgroup::`` annotation when running in GitHub Actions."""
    if _is_github_actions():
        print("::endgroup::", file=sys.stderr, flush=True)


def _emit_decision_summary(summary: dict[str, Any]) -> None:
    """Emit a structured JSON decision summary to stdout.

    The summary captures the full decision path taken by the orchestrator
    so that CI logs are self-documenting and diagnosable without digging
    through raw log text.
    """
    _log_group("AI PR Loop — Decision Summary")
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")
    sys.stdout.flush()
    _log_endgroup()


# Exit codes used by the AI PR loop orchestrator.
#
# These codes are consumed by the calling CI workflow (.github/workflows/ai-pr-loop.yml).
# Non-zero codes are intentional — they signal distinct outcomes to the workflow so it
# can decide whether to retry, re-trigger, or halt:
#
#   EXIT_REPAIR_DISPATCHED (5): A repair was posted via @copilot comment.  The Copilot
#       agent commits a fix, which triggers a new workflow_run event and re-runs this
#       orchestrator automatically.  The non-zero exit marks the current job as failed
#       (expected) to clearly signal that a repair cycle was initiated rather than a
#       clean pass.  Changing this to 0 would make repair dispatches indistinguishable
#       from "nothing to do" in CI logs and status checks.
EXIT_SUCCESS = 0
EXIT_GUARD_BLOCKED = 1
EXIT_MALFORMED_EVENT = 2
EXIT_MERGE_BLOCKED = 3
EXIT_METADATA_FAILED = 4
EXIT_REPAIR_DISPATCHED = 5

# Check run names the orchestrator waits for and evaluates for pass/fail.
# Only checks representing actionable code failures (fixable by the AI agent)
# are included. All other checks are ignored entirely.
_DEFAULT_ACTIONABLE_CHECK_NAMES = frozenset(
    {
        "Tests ✅",
        "Markdown Lint ✅",
        "Workflow Tests ✅",
        "Code scanning results / CodeQL",
    }
)


def _is_ci_completion_event(event_payload: EventPayload) -> bool:
    """Return True when this run was triggered by CI-completion."""
    return event_payload.action == "completed"


def _is_review_submission_event(event_payload: EventPayload) -> bool:
    """Return True when this run was triggered by a PR review submission."""
    return event_payload.action == "submitted"


def _is_issue_comment_created(event_payload: EventPayload) -> bool:
    """Return True when this run was triggered by an ``issue_comment`` create event."""
    return event_payload.action == "comment_created"


def _count_commits_above_merge_base(
    provider: CIPlatformProvider,
    *,
    base_branch: str,
    head_sha: str,
) -> int:
    """Return commit count above merge-base, defaulting to 1 when unsupported."""
    counter = getattr(provider, "count_commits_above_merge_base", None)
    if not callable(counter):
        logger.info("Provider does not expose commit-count probe; treating post-repair squash as not needed")
        return 1
    count = counter(base_branch=base_branch, head_sha=head_sha)
    return int(count)


def _apply_comment_triggered_post_repair_guards(
    pr_number: int,
    pr_meta: PRMetadata,
    summary: dict[str, Any],
) -> int | None:
    """Apply fail-closed guards before comment-triggered post-repair squash."""
    if check_fork_pr(pr_meta.head_repo_full_name, pr_meta.base_repo_full_name):
        logger.info(
            "PR #%d comment-triggered post-repair squash blocked for fork PR (head=%s, base=%s)",
            pr_number,
            pr_meta.head_repo_full_name,
            pr_meta.base_repo_full_name,
        )
        summary["guards"] = {"blocked_by": "fork_pr"}
        summary["decision"] = "blocked"
        summary["reason"] = "fork_pr"
        summary["exit_code"] = EXIT_GUARD_BLOCKED
        return EXIT_GUARD_BLOCKED

    should_skip, flag = check_exclusion_labels(pr_meta.labels)
    if should_skip or flag == "do_not_merge":
        blocked_by = "exclusion_label" if should_skip else "do_not_merge"
        label = LABEL_SKIP_ENTIRELY if should_skip else LABEL_NO_AUTO_MERGE
        logger.info(
            "PR #%d comment-triggered post-repair squash blocked by label guard (%s)",
            pr_number,
            label,
        )
        summary["guards"] = {"blocked_by": blocked_by, "label": label}
        summary["decision"] = "blocked"
        summary["reason"] = blocked_by
        summary["exit_code"] = EXIT_GUARD_BLOCKED
        return EXIT_GUARD_BLOCKED

    return None


def _is_wip_title(title: str) -> bool:
    """Return True when a PR title is explicitly marked work-in-progress."""
    return title.upper().startswith("[WIP]")


def _get_not_ready_reason(pr_meta: PRMetadata, files: list[str]) -> str | None:
    """Return a reason when the PR is not ready for review or merge."""
    if _is_wip_title(pr_meta.title):
        return "wip_title"
    if not files:
        return "no_changes"
    return None


def _normalize_review_body(body: str) -> str:
    """Normalize review body text for robust substring checks.

    GitHub review bodies can contain typographic apostrophes depending on the
    source client, so normalize them to straight apostrophes before matching.
    """
    return body.replace("’", "'").casefold()


def _get_copilot_review_request_skip_reason(
    pr_meta: PRMetadata,
    copilot_review: ReviewInfo | None,
) -> str | None:
    """Return a reason to skip requesting Copilot review, if any."""
    requested_reviewers = {reviewer.casefold() for reviewer in pr_meta.requested_reviewers}
    if any(login.casefold() in requested_reviewers for login in COPILOT_LOGINS):
        return "copilot_already_requested"
    if (
        copilot_review is not None
        and copilot_review.user in COPILOT_LOGINS
        and copilot_review.state == "COMMENTED"
        and "wasn't able to review any files" in _normalize_review_body(copilot_review.body)
    ):
        return "copilot_no_reviewable_files"
    return None


def _request_copilot_review_if_needed(
    provider: CIPlatformProvider,
    pr_number: int,
    pr_meta: PRMetadata,
    copilot_review: ReviewInfo | None,
    *,
    failure_context: str,
) -> str | None:
    """Request Copilot review unless it is already pending or already exhausted."""
    skip_reason = _get_copilot_review_request_skip_reason(pr_meta, copilot_review)
    if skip_reason:
        logger.info(
            "PR #%d skipping Copilot review request (reason=%s)",
            pr_number,
            skip_reason,
        )
        return skip_reason
    try:
        provider.request_reviewer(pr_number, COPILOT_REVIEWER_LOGIN)
    except Exception as exc:
        logger.warning(
            "Failed to request Copilot review for %s PR #%d: %s",
            failure_context,
            pr_number,
            exc,
        )
    return None


def run_ai_pr_loop(
    provider: CIPlatformProvider,
    event_payload: EventPayload,
    *,
    actionable_check_names: frozenset[str] | None = None,
) -> int:
    """Run the AI PR loop state machine.

    Implements the full orchestration sequence:
    1. Validate event payload
    2. Resolve PR metadata
    3. Evaluate guards (privileged paths, Docker, fork, labels, dedup, cycle)
    4. Check CI status
    5. Evaluate reviews
    6. Decide: dispatch repair, approve, or merge

    When actionable Copilot review comments (CHANGES_REQUESTED, or COMMENTED
    with inline suggestions) or failing CI checks are detected, a
    @copilot-tagged comment is posted to trigger an AI agent repair session
    (FR-001, FR-002).

    Before approval, the orchestrator also:
    - Publishes draft PRs and requests Copilot review (returns "published_awaiting_review")
    - Requests Copilot review when none has been submitted yet (returns "awaiting_copilot_review")

    The orchestrator only approves and merges after a non-actionable Copilot
    review (APPROVED, or COMMENTED with 0 inline comments) has been submitted.

    A structured JSON decision summary is emitted at the end of each run
    capturing the full decision path for diagnosability.

    Args:
        provider: CI platform provider for API interactions.
        event_payload: Normalized event payload from the trigger.
        actionable_check_names: Optional set of check run names to evaluate
            during CI gating. Checks not in this set are ignored. Defaults to
            ``_DEFAULT_ACTIONABLE_CHECK_NAMES`` if not provided.

    Returns:
        Exit code (0 = success, non-zero = blocked/error).
    """
    if actionable_check_names is None:
        actionable_check_names = _DEFAULT_ACTIONABLE_CHECK_NAMES

    # Accumulator for the decision summary emitted at the end of the run.
    summary: dict[str, Any] = {
        "event": {
            "pr_number": event_payload.pr_number,
            "head_sha": event_payload.head_sha,
            "action": event_payload.action,
        },
    }

    # Step 1: Validate we have a PR to work with
    if event_payload.pr_number == 0:
        logger.warning("No PR number in event payload, skipping")
        summary["decision"] = "skip"
        summary["reason"] = "no_pr_number"
        summary["exit_code"] = EXIT_SUCCESS
        _emit_decision_summary(summary)
        return EXIT_SUCCESS

    pr_number = event_payload.pr_number

    # Step 2: Resolve full PR metadata
    _log_group("Step 2: Resolve PR metadata")
    try:
        pr_meta = provider.get_pr_metadata(pr_number)
    except Exception as exc:
        logger.error("Failed to get PR metadata for #%d: %s", pr_number, exc)
        _emit_error({"error": "metadata_resolution_failed", "pr_number": pr_number, "detail": str(exc)})
        summary["decision"] = "error"
        summary["reason"] = "metadata_resolution_failed"
        summary["error"] = str(exc)
        summary["exit_code"] = EXIT_METADATA_FAILED
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_METADATA_FAILED
    logger.info("PR #%d metadata resolved: head_sha=%s, base=%s", pr_number, pr_meta.head_sha, pr_meta.base_branch)
    _log_endgroup()

    # Step 2b: Comment-triggered deferred post-repair squash finalization.
    # This path intentionally skips merge-only logic, but still re-applies
    # fork/label guards before any force-push behavior.
    if _is_issue_comment_created(event_payload):
        _log_group("Step 2b: Post-repair squash finalization")
        summary["post_repair"] = {"phase": "comment_triggered"}
        sender_login = event_payload.sender_login
        if not sender_login or sender_login not in COPILOT_COMMENT_LOGINS:
            summary["decision"] = "post_repair_squash_not_needed"
            summary["reason"] = "non_copilot_comment"
            summary["exit_code"] = EXIT_SUCCESS
            _log_endgroup()
            _emit_decision_summary(summary)
            return EXIT_SUCCESS

        guard_exit = _apply_comment_triggered_post_repair_guards(pr_number, pr_meta, summary)
        if guard_exit is not None:
            _log_endgroup()
            _emit_decision_summary(summary)
            return guard_exit

        try:
            reviews = provider.list_reviews(pr_number)
        except Exception as exc:
            logger.error("Failed to list reviews for PR #%d during comment finalization: %s", pr_number, exc)
            summary["decision"] = "error"
            summary["reason"] = "reviews_listing_failed"
            summary["error"] = str(exc)
            summary["exit_code"] = EXIT_METADATA_FAILED
            _log_endgroup()
            _emit_decision_summary(summary)
            return EXIT_METADATA_FAILED

        prior_copilot_reviews = [
            r
            for r in reviews
            if r.user in COPILOT_LOGINS
            and r.commit_sha
            and r.commit_sha != pr_meta.head_sha
            and r.state in ("CHANGES_REQUESTED", "COMMENTED")
        ]
        prior_review_id = 0
        if prior_copilot_reviews:
            prior_copilot_reviews.sort(key=lambda r: r.id, reverse=True)
            prior_review = prior_copilot_reviews[0]
            if prior_review.state == "CHANGES_REQUESTED":
                prior_review_id = prior_review.id
            else:
                try:
                    if provider.list_review_comments(pr_number, prior_review.id):
                        prior_review_id = prior_review.id
                except Exception:
                    # Fail closed when comments cannot be fetched.
                    prior_review_id = prior_review.id

        if not prior_review_id:
            summary["decision"] = "post_repair_squash_not_needed"
            summary["reason"] = "no_prior_actionable_review"
            summary["exit_code"] = EXIT_SUCCESS
            _log_endgroup()
            _emit_decision_summary(summary)
            return EXIT_SUCCESS

        try:
            commit_count = _count_commits_above_merge_base(
                provider,
                base_branch=pr_meta.base_branch,
                head_sha=pr_meta.head_sha,
            )
        except Exception as exc:
            logger.error("Failed to count post-repair commits for PR #%d: %s", pr_number, exc)
            summary["decision"] = "error"
            summary["reason"] = "post_repair_commit_count_failed"
            summary["error"] = str(exc)
            summary["exit_code"] = EXIT_METADATA_FAILED
            _log_endgroup()
            _emit_decision_summary(summary)
            return EXIT_METADATA_FAILED

        if commit_count <= 1:
            summary["post_repair"] = {
                "phase": "comment_triggered",
                "review_id": prior_review_id,
                "commit_count": commit_count,
            }
            summary["decision"] = "post_repair_squash_not_needed"
            summary["reason"] = "already_squashed_or_single_commit"
            summary["exit_code"] = EXIT_SUCCESS
            _log_endgroup()
            _emit_decision_summary(summary)
            return EXIT_SUCCESS

        try:
            provider.squash_post_repair(
                pr_number=pr_number,
                base_branch=pr_meta.base_branch,
                head_branch=pr_meta.head_branch,
                head_sha=pr_meta.head_sha,
            )
        except Exception as exc:
            logger.error("Post-repair squash finalization failed for PR #%d: %s", pr_number, exc)
            summary["decision"] = "error"
            summary["reason"] = "post_repair_squash_failed"
            summary["error"] = str(exc)
            summary["exit_code"] = EXIT_MERGE_BLOCKED
            _log_endgroup()
            _emit_decision_summary(summary)
            return EXIT_MERGE_BLOCKED

        summary["post_repair"] = {
            "phase": "comment_triggered",
            "review_id": prior_review_id,
            "commit_count": commit_count,
            "squashed": True,
        }
        summary["decision"] = "post_repair_squash_completed"
        summary["exit_code"] = EXIT_SUCCESS
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_SUCCESS

    # Step 3: Evaluate guards
    _log_group("Step 3: Evaluate guards")

    # 3a: Fork PR guard
    if check_fork_pr(pr_meta.head_repo_full_name, pr_meta.base_repo_full_name):
        logger.info(
            "PR #%d is from a fork (head=%s, base=%s) — skipping",
            pr_number,
            pr_meta.head_repo_full_name,
            pr_meta.base_repo_full_name,
        )
        summary["guards"] = {"blocked_by": "fork_pr"}
        summary["decision"] = "blocked"
        summary["reason"] = "fork_pr"
        summary["exit_code"] = EXIT_GUARD_BLOCKED
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_GUARD_BLOCKED

    # 3b: Exclusion labels
    should_skip, flag = check_exclusion_labels(pr_meta.labels)
    if should_skip:
        logger.info("PR #%d has exclusion label '%s' — skipping entirely", pr_number, LABEL_SKIP_ENTIRELY)
        summary["guards"] = {"blocked_by": "exclusion_label", "label": LABEL_SKIP_ENTIRELY}
        summary["decision"] = "blocked"
        summary["reason"] = "exclusion_label"
        summary["exit_code"] = EXIT_GUARD_BLOCKED
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_GUARD_BLOCKED

    do_not_merge = flag == "do_not_merge"

    # 3c: Privileged paths
    try:
        files = provider.list_pr_files(pr_number)
    except Exception as exc:
        logger.error("Failed to list changed files for PR #%d: %s", pr_number, exc)
        summary["decision"] = "error"
        summary["reason"] = "pr_files_listing_failed"
        summary["error"] = str(exc)
        summary["exit_code"] = EXIT_METADATA_FAILED
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_METADATA_FAILED
    if check_privileged_paths(files):
        privileged = [f for f in files if any(f.startswith(p) for p in PRIVILEGED_PREFIXES) and not f.endswith(".md")]
        logger.info("PR #%d touches privileged paths %s — requires human review", pr_number, privileged)
        summary["guards"] = {"blocked_by": "privileged_paths", "files": privileged}
        summary["decision"] = "blocked"
        summary["reason"] = "privileged_paths"
        summary["exit_code"] = EXIT_GUARD_BLOCKED
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_GUARD_BLOCKED

    # 3d: Docker files
    if check_docker_files(files):
        logger.info("PR #%d touches Docker files — requires human review", pr_number)
        summary["guards"] = {"blocked_by": "docker_files"}
        summary["decision"] = "blocked"
        summary["reason"] = "docker_files"
        summary["exit_code"] = EXIT_GUARD_BLOCKED
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_GUARD_BLOCKED

    logger.info("PR #%d passed path guards (files=%d, do_not_merge=%s)", pr_number, len(files), do_not_merge)
    _log_endgroup()

    # Step 4: Check CI status
    _log_group("Step 4: Check CI status")
    try:
        check_runs = provider.list_check_runs(pr_meta.head_sha)
    except Exception as exc:
        logger.error("Failed to list check runs for PR #%d: %s", pr_number, exc)
        summary["decision"] = "error"
        summary["reason"] = "check_runs_listing_failed"
        summary["error"] = str(exc)
        summary["exit_code"] = EXIT_METADATA_FAILED
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_METADATA_FAILED
    has_unknown_conclusion = False
    any_failed = False
    any_pending = False
    failed_checks: list[CheckRunStatus] = []
    ignored_checks = 0
    actionable_seen = 0
    for cr in check_runs:
        # Only evaluate checks we can actually fix — ignore everything else
        if cr.name not in actionable_check_names:
            ignored_checks += 1
            logger.info("  check '%s' — ignored (not actionable)", cr.name)
            continue
        actionable_seen += 1
        if cr.status != "completed":
            any_pending = True
            logger.info("  check '%s' — pending (status=%s)", cr.name, cr.status)
        elif cr.conclusion == "failure":
            any_failed = True
            failed_checks.append(cr)
            logger.info("  check '%s' — FAILED", cr.name)
        elif cr.conclusion not in ("success", "neutral", "skipped"):
            has_unknown_conclusion = True
            logger.info("  check '%s' — unknown conclusion '%s'", cr.name, cr.conclusion)
        else:
            logger.info("  check '%s' — %s", cr.name, cr.conclusion)

    # If no actionable check runs have appeared yet (e.g. early in the PR lifecycle,
    # before gate jobs are created), treat this as pending rather than proceeding to
    # approve/merge — required checks may not have started yet.
    if actionable_seen == 0:
        any_pending = True
        logger.info(
            "PR #%d — no actionable checks observed yet; treating as pending",
            pr_number,
        )

    ci_summary: dict[str, Any] = {
        "total": len(check_runs),
        "actionable": actionable_seen,
        "ignored": ignored_checks,
        "pending": any_pending,
        "failed": [cr.name for cr in failed_checks],
        "has_unknown_conclusion": has_unknown_conclusion,
    }
    summary["ci"] = ci_summary

    if any_pending:
        logger.info("PR #%d has pending checks — waiting for CI to complete", pr_number)
        summary["decision"] = "wait"
        summary["reason"] = "checks_pending"
        summary["exit_code"] = EXIT_SUCCESS
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_SUCCESS
    _log_endgroup()

    # 3e: Deduplication — checked after CI pending short-circuit so that
    # re-triggers while CI is still running don't consume the dispatch budget.
    # Review submission events are external triggers (Copilot or human submitting
    # a review) and are not caused by the loop itself, so they always bypass
    # deduplication regardless of how many repair dispatches have already occurred.
    _log_group("Step 3e–3f: Deduplication and cycle guards")
    dedup_sha = event_payload.head_sha or pr_meta.head_sha
    dedup_skip = False
    dedup_count = 0
    dedup_bypassed = False
    if _is_review_submission_event(event_payload):
        dedup_bypassed = True
        logger.info("PR #%d — review submission event; dedup check bypassed", pr_number)
    else:
        try:
            dedup_skip, dedup_count = check_deduplication(provider, pr_number, dedup_sha)
        except Exception as exc:
            logger.error("Deduplication check failed for PR #%d: %s", pr_number, exc)
            summary["decision"] = "error"
            summary["reason"] = "deduplication_failed"
            summary["error"] = str(exc)
            summary["exit_code"] = EXIT_METADATA_FAILED
            _log_endgroup()
            _emit_decision_summary(summary)
            return EXIT_METADATA_FAILED
        if dedup_skip:
            logger.info(
                "PR #%d dispatch limit reached for sha=%s (count=%d) — skipping",
                pr_number,
                dedup_sha[:8],
                dedup_count,
            )
            summary["guards"] = {"blocked_by": "deduplication", "sha": dedup_sha[:8], "count": dedup_count}
            summary["decision"] = "blocked"
            summary["reason"] = "dedup_limit"
            summary["exit_code"] = EXIT_GUARD_BLOCKED
            _log_endgroup()
            _emit_decision_summary(summary)
            return EXIT_GUARD_BLOCKED

    # 3f: Cycle limit — checked after CI pending short-circuit so that
    # re-triggers while CI is still running don't exhaust the cycle budget.
    try:
        cycle_reached, cycle_count = check_cycle_limit(provider, pr_number)
    except Exception as exc:
        logger.error("Cycle limit check failed for PR #%d: %s", pr_number, exc)
        summary["decision"] = "error"
        summary["reason"] = "cycle_limit_check_failed"
        summary["error"] = str(exc)
        summary["exit_code"] = EXIT_METADATA_FAILED
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_METADATA_FAILED
    if cycle_reached:
        logger.info("PR #%d cycle limit reached (count=%d) — skipping", pr_number, cycle_count)
        summary["guards"] = {"blocked_by": "cycle_limit", "count": cycle_count}
        summary["decision"] = "blocked"
        summary["reason"] = "cycle_limit"
        summary["exit_code"] = EXIT_GUARD_BLOCKED
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_GUARD_BLOCKED
    if dedup_bypassed:
        logger.info(
            "PR #%d dedup bypassed (review submission) and cycle (count=%d) guards passed",
            pr_number,
            cycle_count,
        )
    else:
        logger.info("PR #%d passed dedup (count=%d) and cycle (count=%d) guards", pr_number, dedup_count, cycle_count)
    _log_endgroup()

    # Step 5: Evaluate reviews
    # Collapse to effective latest state per reviewer (highest review.id wins).
    # All COPILOT_LOGINS aliases are normalized to a single canonical key so
    # that a later APPROVED from any Copilot alias supersedes an earlier
    # COMMENTED or CHANGES_REQUESTED posted under a different alias.
    _log_group("Step 5: Evaluate reviews")
    _COPILOT_KEY = "copilot"
    try:
        reviews = provider.list_reviews(pr_number)
    except Exception as exc:
        logger.error("Failed to list reviews for PR #%d: %s", pr_number, exc)
        summary["decision"] = "error"
        summary["reason"] = "reviews_listing_failed"
        summary["error"] = str(exc)
        summary["exit_code"] = EXIT_METADATA_FAILED
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_METADATA_FAILED
    current_head_sha = pr_meta.head_sha
    reviews_for_head = [review for review in reviews if not review.commit_sha or review.commit_sha == current_head_sha]
    latest_by_user: dict[str, ReviewInfo] = {}
    for review in reviews_for_head:
        user_key = _COPILOT_KEY if review.user in COPILOT_LOGINS else review.user
        existing = latest_by_user.get(user_key)
        if existing is None or review.id > existing.id:
            latest_by_user[user_key] = review

    effective_reviews = list(latest_by_user.values())
    has_approval = any(r.state == "APPROVED" for r in effective_reviews)
    copilot_actionable_review = False
    any_changes_requested = False
    copilot_review_id = 0
    copilot_review_comments: list[ReviewCommentInfo] = []

    for review in effective_reviews:
        logger.info("  review by '%s' — state=%s (id=%d)", review.user, review.state, review.id)

    # Detect actionable Copilot review (CHANGES_REQUESTED or COMMENTED with
    # inline comments from Copilot).  A COMMENTED review is only actionable
    # when it contains inline comments (i.e. suggestions the author should
    # address).  Comments are cached here so _dispatch_repair() can reuse them
    # without a second API call.
    for review in effective_reviews:
        if review.user in COPILOT_LOGINS and review.state == "CHANGES_REQUESTED":
            copilot_actionable_review = True
            copilot_review_id = review.id
            logger.info("  → Copilot CHANGES_REQUESTED detected (review_id=%d) — actionable", review.id)
            break
        if review.user in COPILOT_LOGINS and review.state == "COMMENTED":
            try:
                comments = provider.list_review_comments(pr_number, review.id)
            except Exception as exc:
                # Fail closed: if we cannot confirm the review has no inline
                # comments, treat it as actionable to avoid merging over
                # suggestions that we failed to fetch.
                logger.warning(
                    "Failed to check review comments for PR #%d review %d — treating review as actionable: %s",
                    pr_number,
                    review.id,
                    exc,
                )
                copilot_actionable_review = True
                copilot_review_id = review.id
                break
            if comments:
                copilot_actionable_review = True
                copilot_review_id = review.id
                copilot_review_comments = list(comments)
                logger.info(
                    "  → Copilot COMMENTED with %d inline comment(s) (review_id=%d) — actionable",
                    len(comments),
                    review.id,
                )
                break
            logger.info("  → Copilot COMMENTED with 0 inline comments (review_id=%d) — not actionable", review.id)
        if review.state == "CHANGES_REQUESTED":
            any_changes_requested = True

    review_summary: dict[str, Any] = {
        "total_raw": len(reviews),
        "total_on_head": len(reviews_for_head),
        "effective": len(effective_reviews),
        "has_approval": has_approval,
        "copilot_actionable": copilot_actionable_review,
        "copilot_review_id": copilot_review_id,
        "any_changes_requested": any_changes_requested,
    }
    summary["reviews"] = review_summary
    _log_endgroup()

    # PR readiness gate — applies regardless of draft status so WIP/no-change
    # PRs never reach repair dispatch, review requests, or merge decisions.
    not_ready_reason = _get_not_ready_reason(pr_meta, files)
    if not_ready_reason is not None:
        logger.info(
            "PR #%d is not ready for Copilot review or merge (draft=%s, reason=%s) — waiting",
            pr_number,
            pr_meta.is_draft,
            not_ready_reason,
        )
        summary["decision"] = "draft_not_ready" if pr_meta.is_draft else "not_ready"
        summary["reason"] = not_ready_reason
        summary["exit_code"] = EXIT_SUCCESS
        _emit_decision_summary(summary)
        return EXIT_SUCCESS

    # Step 6: Dispatch repair decision (only for Copilot reviews and CI failures)
    _log_group("Step 6: Repair decision")
    _copilot_review = latest_by_user.get(_COPILOT_KEY)
    if _is_ci_completion_event(event_payload):
        if any_failed:
            logger.info("PR #%d has actionable CI failures on CI-completion trigger", pr_number)
            decision = _evaluate_repair_decision(
                any_failed=True,
                copilot_actionable_review=False,
                copilot_review_id=0,
                copilot_review_comments=[],
                failed_checks=failed_checks,
            )
            summary["repair"] = {
                "needed": True,
                "type": decision.repair_type,
                "review_id": decision.review_id,
                "failed_checks": [cr.name for cr in decision.failed_checks],
            }
            _log_endgroup()
            ci_repair_failure_reason: list[str] = []
            result = _dispatch_repair(
                provider=provider,
                pr_number=pr_number,
                head_sha=pr_meta.head_sha,
                decision=decision,
                failure_reason_out=ci_repair_failure_reason,
            )
            if result == EXIT_REPAIR_DISPATCHED:
                try:
                    cycle_count = increment_cycle_count(provider, pr_number)
                    summary["repair_cycle"] = {"count": cycle_count}
                except Exception as exc:
                    logger.error("Failed to increment cycle tracker for PR #%d: %s", pr_number, exc)
            summary["decision"] = "repair_dispatched" if result == EXIT_REPAIR_DISPATCHED else "repair_failed"
            if ci_repair_failure_reason:
                summary["reason"] = ci_repair_failure_reason[0]
            summary["exit_code"] = result
            _emit_decision_summary(summary)
            return result

        if copilot_actionable_review and copilot_review_id:
            _log_endgroup()
            _log_group("Step 6b: Post-repair finalization")
            try:
                provider.finalize_post_repair(
                    pr_number=pr_number,
                    base_branch=pr_meta.base_branch,
                    head_branch=pr_meta.head_branch,
                    head_sha=pr_meta.head_sha,
                    review_id=copilot_review_id,
                )
            except Exception as exc:
                logger.error("Post-repair finalization failed for PR #%d: %s", pr_number, exc)
                summary["decision"] = "error"
                summary["reason"] = "post_repair_finalization_failed"
                summary["error"] = str(exc)
                summary["exit_code"] = EXIT_MERGE_BLOCKED
                _log_endgroup()
                _emit_decision_summary(summary)
                return EXIT_MERGE_BLOCKED
            summary["post_repair"] = {"finalized": True, "review_id": copilot_review_id}
            summary["decision"] = "post_repair_soft_finalized"
            summary["exit_code"] = EXIT_SUCCESS
            _log_endgroup()
            _emit_decision_summary(summary)
            return EXIT_SUCCESS

        # No actionable review on HEAD — check for an actionable Copilot review
        # on a prior commit.  When Copilot SWE agent pushes a repair commit the
        # review that triggered the repair targets the old SHA.  After CI passes
        # on the new HEAD we must still soft-finalize (reply, resolve).
        prior_copilot_reviews = [
            r
            for r in reviews
            if r.user in COPILOT_LOGINS
            and r.commit_sha
            and r.commit_sha != current_head_sha
            and r.state in ("CHANGES_REQUESTED", "COMMENTED")
        ]
        if prior_copilot_reviews:
            prior_copilot_reviews.sort(key=lambda r: r.id, reverse=True)
            prior_review = prior_copilot_reviews[0]
            prior_actionable = False
            prior_review_id = 0
            if prior_review.state == "CHANGES_REQUESTED":
                prior_actionable = True
                prior_review_id = prior_review.id
            elif prior_review.state == "COMMENTED":
                try:
                    comments = provider.list_review_comments(pr_number, prior_review.id)
                    if comments:
                        prior_actionable = True
                        prior_review_id = prior_review.id
                except Exception:
                    # Fail closed: treat as actionable when comments cannot be fetched.
                    prior_actionable = True
                    prior_review_id = prior_review.id
            if prior_actionable and prior_review_id:
                logger.info(
                    "PR #%d: actionable Copilot review %d targets prior commit %s — post-repair scenario",
                    pr_number,
                    prior_review_id,
                    prior_review.commit_sha,
                )
                _log_endgroup()
                _log_group("Step 6b: Post-repair finalization (prior-commit review)")
                try:
                    provider.finalize_post_repair(
                        pr_number=pr_number,
                        base_branch=pr_meta.base_branch,
                        head_branch=pr_meta.head_branch,
                        head_sha=pr_meta.head_sha,
                        review_id=prior_review_id,
                    )
                except Exception as exc:
                    logger.error("Post-repair finalization failed for PR #%d: %s", pr_number, exc)
                    summary["decision"] = "error"
                    summary["reason"] = "post_repair_finalization_failed"
                    summary["error"] = str(exc)
                    summary["exit_code"] = EXIT_MERGE_BLOCKED
                    _log_endgroup()
                    _emit_decision_summary(summary)
                    return EXIT_MERGE_BLOCKED
                summary["post_repair"] = {
                    "finalized": True,
                    "review_id": prior_review_id,
                    "prior_commit": True,
                }
                summary["decision"] = "post_repair_soft_finalized"
                summary["exit_code"] = EXIT_SUCCESS
                _log_endgroup()
                _emit_decision_summary(summary)
                return EXIT_SUCCESS

        # No actionable review and no failures — ensure a Copilot review is
        # requested so the gate can pass on the current HEAD.
        if pr_meta.is_draft:
            logger.info(
                "PR #%d CI passed with no actionable Copilot review, but PR is draft — waiting for publish",
                pr_number,
            )
            summary["repair"] = {"needed": False}
            summary["decision"] = "draft_not_ready"
            summary["reason"] = "awaiting_publish"
            summary["exit_code"] = EXIT_SUCCESS
            _log_endgroup()
            _emit_decision_summary(summary)
            return EXIT_SUCCESS
        summary["repair"] = {"needed": False}
        logger.info("PR #%d CI passed, no Copilot review on HEAD — requesting review", pr_number)
        request_skip_reason = _request_copilot_review_if_needed(
            provider,
            pr_number,
            pr_meta,
            _copilot_review,
            failure_context="PR",
        )
        summary["decision"] = "awaiting_copilot_review_after_ci"
        if request_skip_reason is not None:
            summary["reason"] = request_skip_reason
        summary["exit_code"] = EXIT_SUCCESS
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_SUCCESS

    decision = _evaluate_repair_decision(
        any_failed=any_failed,
        copilot_actionable_review=copilot_actionable_review,
        copilot_review_id=copilot_review_id,
        copilot_review_comments=copilot_review_comments,
        failed_checks=failed_checks,
    )

    if decision.repair_needed:
        logger.info(
            "PR #%d repair needed (type=%s, review_id=%d, failed_checks=%d)",
            pr_number,
            decision.repair_type,
            decision.review_id,
            len(decision.failed_checks),
        )
        summary["repair"] = {
            "needed": True,
            "type": decision.repair_type,
            "review_id": decision.review_id,
            "failed_checks": [cr.name for cr in decision.failed_checks],
        }
        _log_endgroup()
        repair_failure_reason: list[str] = []
        result = _dispatch_repair(
            provider=provider,
            pr_number=pr_number,
            head_sha=pr_meta.head_sha,
            decision=decision,
            failure_reason_out=repair_failure_reason,
        )
        if result == EXIT_REPAIR_DISPATCHED:
            try:
                cycle_count = increment_cycle_count(provider, pr_number)
                summary["repair_cycle"] = {"count": cycle_count}
            except Exception as exc:
                logger.error("Failed to increment cycle tracker for PR #%d: %s", pr_number, exc)
        summary["decision"] = "repair_dispatched" if result == EXIT_REPAIR_DISPATCHED else "repair_failed"
        if repair_failure_reason:
            summary["reason"] = repair_failure_reason[0]
        summary["exit_code"] = result
        _emit_decision_summary(summary)
        return result
    logger.info("PR #%d no repair needed", pr_number)
    summary["repair"] = {"needed": False}
    _log_endgroup()

    # Step 7: Merge gate
    # Note: any_failed and copilot_actionable_review are guaranteed False here —
    # both conditions trigger repair dispatch in Step 6 which returns before
    # reaching this point.
    _log_group("Step 7–9: Merge gate")
    if has_unknown_conclusion:
        logger.info(
            "PR #%d has checks with non-success conclusions — cannot merge",
            pr_number,
        )
        summary["decision"] = "blocked"
        summary["reason"] = "unknown_check_conclusions"
        summary["exit_code"] = EXIT_MERGE_BLOCKED
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_MERGE_BLOCKED

    if any_changes_requested:
        logger.info(
            "PR #%d has non-Copilot changes requested — waiting for author updates (not dispatching repair)",
            pr_number,
        )
        summary["decision"] = "wait"
        summary["reason"] = "human_changes_requested"
        summary["exit_code"] = EXIT_SUCCESS
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_SUCCESS

    if do_not_merge:
        logger.info("PR #%d ready but do-not-auto-merge label present — skipping merge", pr_number)
        summary["decision"] = "skip_merge"
        summary["reason"] = "do_not_auto_merge_label"
        summary["exit_code"] = EXIT_SUCCESS
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_SUCCESS

    if not _is_review_submission_event(event_payload):
        logger.info("PR #%d is ready but waiting for pull_request_review trigger to merge", pr_number)
        summary["decision"] = "wait"
        summary["reason"] = "awaiting_pull_request_review_event"
        summary["exit_code"] = EXIT_SUCCESS
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_SUCCESS

    # Step 7a: Draft PR check — publish before attempting approval or merge.
    # A draft PR cannot be merged; publishing it also allows Copilot to review.
    if pr_meta.is_draft:
        logger.info("PR #%d is a draft — publishing and requesting Copilot review", pr_number)
        try:
            provider.squash_before_publish(
                pr_number=pr_number,
                base_branch=pr_meta.base_branch,
                head_branch=pr_meta.head_branch,
                head_sha=pr_meta.head_sha,
            )
        except Exception as exc:
            logger.error("Failed to squash before publish for PR #%d: %s", pr_number, exc, exc_info=True)
            summary["squash_error"] = str(exc)
            summary["decision"] = "error"
            summary["reason"] = "squash_before_publish_failed"
            summary["exit_code"] = EXIT_MERGE_BLOCKED
            _log_endgroup()
            _emit_decision_summary(summary)
            return EXIT_MERGE_BLOCKED
        try:
            provider.publish_pr(pr_number)
        except Exception as exc:
            logger.error("Failed to publish draft PR #%d: %s", pr_number, exc)
            summary["decision"] = "error"
            summary["reason"] = "publish_failed"
            summary["error"] = str(exc)
            summary["exit_code"] = EXIT_MERGE_BLOCKED
            _log_endgroup()
            _emit_decision_summary(summary)
            return EXIT_MERGE_BLOCKED
        # Publishing already triggers GitHub's automatic Copilot review on the
        # ready_for_review event, but we explicitly request it as a
        # belt-and-suspenders safety net.
        request_skip_reason = _request_copilot_review_if_needed(
            provider,
            pr_number,
            pr_meta,
            _copilot_review,
            failure_context="draft",
        )
        summary["decision"] = "published_awaiting_review"
        if request_skip_reason is not None:
            summary["reason"] = request_skip_reason
        summary["exit_code"] = EXIT_SUCCESS
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_SUCCESS

    # Step 7b: Require a Copilot review before approving or merging.
    # The orchestrator must not auto-approve until Copilot has reviewed the PR
    # (either APPROVED, or COMMENTED with 0 inline comments — both land here
    # because actionable reviews are dispatched for repair in Step 6).
    # Only APPROVED, COMMENTED, and CHANGES_REQUESTED count as effective
    # review states.  DISMISSED or PENDING reviews are treated as "no review"
    # so the loop requests a fresh one.
    _EFFECTIVE_REVIEW_STATES = frozenset({"APPROVED", "COMMENTED", "CHANGES_REQUESTED"})
    has_copilot_review = _copilot_review is not None and _copilot_review.state in _EFFECTIVE_REVIEW_STATES
    if not has_copilot_review:
        logger.info("PR #%d has no Copilot review yet — requesting review and waiting", pr_number)
        request_skip_reason = _request_copilot_review_if_needed(
            provider,
            pr_number,
            pr_meta,
            _copilot_review,
            failure_context="PR",
        )
        summary["decision"] = "awaiting_copilot_review"
        if request_skip_reason is not None:
            summary["reason"] = request_skip_reason
        summary["exit_code"] = EXIT_SUCCESS
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_SUCCESS

    # Step 8: Approve if needed
    if not has_approval:
        logger.info("PR #%d has no approval — auto-approving", pr_number)
        try:
            provider.approve_pr(pr_number, pr_meta.head_sha, "Auto-approved by AI PR loop")
        except Exception as exc:
            logger.error("Failed to auto-approve PR #%d: %s", pr_number, exc)
            summary["decision"] = "error"
            summary["reason"] = "approval_failed"
            summary["error"] = str(exc)
            summary["exit_code"] = EXIT_MERGE_BLOCKED
            _log_endgroup()
            _emit_decision_summary(summary)
            return EXIT_MERGE_BLOCKED
        summary["auto_approved"] = True
    else:
        summary["auto_approved"] = False

    # Step 9: Merge
    try:
        provider.merge_pr(pr_number, pr_meta.head_sha, "squash")
        logger.info("PR #%d merged successfully", pr_number)
    except Exception as exc:
        logger.error("Failed to merge PR #%d: %s", pr_number, exc)
        summary["decision"] = "error"
        summary["reason"] = "merge_failed"
        summary["error"] = str(exc)
        summary["exit_code"] = EXIT_MERGE_BLOCKED
        _log_endgroup()
        _emit_decision_summary(summary)
        return EXIT_MERGE_BLOCKED

    summary["decision"] = "merged"
    summary["exit_code"] = EXIT_SUCCESS
    _log_endgroup()
    _emit_decision_summary(summary)
    return EXIT_SUCCESS


def _evaluate_repair_decision(
    *,
    any_failed: bool,
    copilot_actionable_review: bool,
    copilot_review_id: int,
    copilot_review_comments: list[ReviewCommentInfo],
    failed_checks: list[CheckRunStatus],
) -> RepairDecision:
    """Evaluate whether a repair dispatch is needed and determine the type.

    Two repair sources exist: Copilot review feedback and failing CI checks.
    Only Copilot reviews trigger review-based repairs (CHANGES_REQUESTED, or
    COMMENTED with inline comments); human reviews never trigger repair dispatch.
    Failing CI checks independently trigger CI repairs regardless of review state.

    Args:
        any_failed: True if any CI check has failed.
        copilot_actionable_review: True if Copilot posted an actionable review
            (CHANGES_REQUESTED, or COMMENTED with inline comments).
        copilot_review_id: ID of the actionable Copilot review (0 if none).
        copilot_review_comments: Rich review comment metadata pre-fetched during
            detection (populated for COMMENTED reviews; empty for
            CHANGES_REQUESTED so that ``_dispatch_repair`` fetches lazily).
        failed_checks: List of failed check runs.

    Returns:
        RepairDecision indicating whether and what type of repair is needed.
    """
    has_review_repair = copilot_actionable_review
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
        review_comments=tuple(copilot_review_comments),
        failed_checks=tuple(failed_checks),
    )


def _dispatch_repair(
    *,
    provider: CIPlatformProvider,
    pr_number: int,
    head_sha: str,
    decision: RepairDecision,
    failure_reason_out: list[str] | None = None,
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
        failure_reason_out: Optional list to receive a short diagnostic
            error message when dispatch fails.

    Returns:
        EXIT_REPAIR_DISPATCHED on success, EXIT_MERGE_BLOCKED on failure.
    """
    # Collect rich review comment data when review repair is needed.
    # For COMMENTED reviews the comments were already fetched during detection
    # and are stored in decision.review_comments — reuse them to avoid a
    # second API call and potential inconsistency if comments change between
    # calls.  For CHANGES_REQUESTED reviews, decision.review_comments is empty
    # so we fetch lazily here.
    review_comments: list[ReviewCommentInfo] = []
    if decision.review_id and decision.repair_type in ("review", "both"):
        if decision.review_comments:
            review_comments = list(decision.review_comments)
        else:
            try:
                review_comments = provider.list_review_comments(pr_number, decision.review_id)
            except Exception as exc:
                logger.warning("Failed to fetch review comments for PR #%d: %s", pr_number, exc)

    try:
        comment_id = provider.dispatch_repair(
            pr_number=pr_number,
            head_sha=head_sha,
            repair_type=decision.repair_type,
            failed_checks=list(decision.failed_checks),
            review_comments=review_comments,
            review_id=decision.review_id,
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
        if failure_reason_out is not None:
            failure_reason_out.append(str(exc))
        return EXIT_MERGE_BLOCKED


def _emit_error(error_data: dict) -> None:
    """Emit structured error JSON to stderr."""
    json.dump(error_data, sys.stderr)
    sys.stderr.write("\n")
