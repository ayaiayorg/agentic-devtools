"""Snapshot builder for the post-agent evaluator.

Gathers all PR state needed for classification into an immutable
PostAgentSnapshot dataclass.
"""

from __future__ import annotations

import logging

from ..guards import REPAIR_SATISFIED_MARKER, REVIEW_ID_MARKER_RE
from ..models import COPILOT_COMMENT_LOGINS, COPILOT_LOGINS
from ..provider import CIPlatformProvider
from .lock import check_lock_status
from .models import CommentInfo, PostAgentSnapshot, ThreadInfo

logger = logging.getLogger(__name__)

_SENTINEL_MARKER = "<!-- copilot-agent-result -->"


def _get_review_thread_statuses(
    provider: CIPlatformProvider,
    pr_number: int,
) -> dict[int, tuple[bool, bool]]:
    """Map review comment IDs to (is_resolved, has_reply) when provider supports it."""
    list_review_thread_states = getattr(provider, "list_review_thread_states", None)
    if not callable(list_review_thread_states):
        return {}
    return list_review_thread_states(pr_number)


def _get_latest_agent_comment(
    provider: CIPlatformProvider,
    pr_number: int,
    comments: list | None = None,
) -> CommentInfo | None:
    """Get the latest Copilot-authored issue comment if supported by provider."""
    if comments is None:
        list_issue_comments = getattr(provider, "list_issue_comments", None)
        if not callable(list_issue_comments):
            return None
        comments = list_issue_comments(pr_number)
    copilot_comments = [c for c in comments if c.author in COPILOT_COMMENT_LOGINS]
    if not copilot_comments:
        return None

    latest = max(copilot_comments, key=lambda c: (c.created_at, c.id))
    return CommentInfo(
        id=latest.id,
        author=latest.author,
        body=latest.body,
        created_at=latest.created_at,
    )


def _has_evaluator_sentinel_comment(
    provider: CIPlatformProvider,
    pr_number: int,
    current_head_sha: str,
    comments: list | None = None,
) -> bool:
    """Return True when any issue comment is an evaluator-synthesized sentinel for the current HEAD.

    Evaluator-synthesized sentinels (from ``synthesize_sentinel()`` / ``verify_and_resolve()``)
    are posted via ``provider.post_comment()`` using the workflow token rather than a Copilot
    login, so they are not captured by ``_get_latest_agent_comment()``.  Scope the check to
    ``current_head_sha`` (first 8 chars) to avoid false positives from older cycle sentinels
    on the same PR.
    """
    if not current_head_sha:
        return False
    head_sha_short = current_head_sha[:8]
    if comments is None:
        list_issue_comments = getattr(provider, "list_issue_comments", None)
        if not callable(list_issue_comments):
            return False
        try:
            comments = list_issue_comments(pr_number)
        except Exception as exc:
            logger.warning("Failed to fetch issue comments for evaluator sentinel check on PR #%d: %s", pr_number, exc)
            return False
    return any(_SENTINEL_MARKER in c.body and head_sha_short in c.body for c in comments)


def build_snapshot(
    provider: CIPlatformProvider,
    pr_number: int,
    repo: str,
    *,
    current_lock_token: str | None = None,
) -> PostAgentSnapshot:
    """Build an immutable snapshot of the PR state for classification.

    Gathers all data needed by ``classify_post_agent_state()`` using
    provider methods. This function performs I/O (via the provider) but
    produces an immutable result suitable for pure classification.

    Args:
        provider: CI platform provider.
        pr_number: Pull request number.
        repo: Full repository name (owner/repo).
        current_lock_token: Lock token held by the current evaluator run, if any.

    Returns:
        Frozen PostAgentSnapshot with all relevant PR state.
    """
    # 1. Get PR metadata for HEAD SHA
    pr_meta = provider.get_pr_metadata(pr_number)
    current_head_sha = pr_meta.head_sha

    # 2. Get reviews to find the latest Copilot review
    reviews = provider.list_reviews(pr_number)
    copilot_reviews = [r for r in reviews if r.user in COPILOT_LOGINS]
    # Sort by ID descending to get the latest
    copilot_reviews.sort(key=lambda r: r.id, reverse=True)

    review_id = 0
    review_commit_sha = ""
    if copilot_reviews:
        latest_review = copilot_reviews[0]
        review_id = latest_review.id
        review_commit_sha = latest_review.commit_sha

    # 3. Determine if HEAD changed since the review
    head_changed = bool(review_commit_sha and current_head_sha and review_commit_sha != current_head_sha)

    def _load_review_threads(target_review_id: int) -> list[ThreadInfo]:
        loaded_threads: list[ThreadInfo] = []
        try:
            thread_statuses: dict[int, tuple[bool, bool]] = {}
            try:
                thread_statuses = _get_review_thread_statuses(provider, pr_number)
            except Exception:
                logger.warning("Failed to fetch review thread statuses for PR #%d", pr_number)

            review_comments = provider.list_review_comments(pr_number, target_review_id)
            for rc in review_comments:
                # Skip synthetic review-body entries — they have no real GitHub
                # thread and must not be used for thread-resolution lookup.
                if rc.id < 0:
                    continue
                is_resolved, has_reply = thread_statuses.get(rc.id, (False, False))
                loaded_threads.append(
                    ThreadInfo(
                        comment_id=rc.id,
                        path=rc.path,
                        start_line=rc.start_line,
                        end_line=rc.end_line,
                        is_resolved=is_resolved,
                        has_reply=has_reply,
                        body=rc.body,
                    )
                )
        except Exception as exc:
            logger.warning("Failed to fetch review comments for review %d: %s", target_review_id, exc)
        return loaded_threads

    # 4. Get review threads (comments from the review)
    threads: list[ThreadInfo] = []
    if review_id:
        threads = _load_review_threads(review_id)

    # 5. Find latest Copilot agent comment (issue comment, not review comment)
    list_issue_comments = getattr(provider, "list_issue_comments", None)
    issue_comments: list = []
    if callable(list_issue_comments):
        try:
            issue_comments = list_issue_comments(pr_number)
        except Exception as exc:
            logger.warning("Failed to fetch issue comments for PR #%d: %s", pr_number, exc)

    latest_agent_comment = _get_latest_agent_comment(provider, pr_number, comments=issue_comments)

    head_sha_short = current_head_sha[:8] if current_head_sha else ""

    # Sentinel is present if:
    # (a) the latest Copilot comment contains the marker and is scoped to the current
    #     HEAD (avoids treating stale prior-cycle sentinels as current completion), or
    # (b) any issue comment contains an evaluator-synthesized sentinel scoped to the
    #     current HEAD (posted via provider.post_comment() by the workflow token, not
    #     a Copilot login, so not captured by _get_latest_agent_comment()).
    has_sentinel = bool(
        (
            latest_agent_comment is not None
            and _SENTINEL_MARKER in latest_agent_comment.body
            and bool(head_sha_short)
            and head_sha_short in latest_agent_comment.body
        )
        or _has_evaluator_sentinel_comment(provider, pr_number, current_head_sha, comments=issue_comments)
    )

    # 6. Check lock status
    lock_status = check_lock_status(provider, pr_number)

    # 7. Get PR diff (prefer post-review range diff when available)
    diff_text = ""
    try:
        if review_commit_sha and head_changed:
            diff_text = provider.get_commit_range_diff(review_commit_sha, current_head_sha)
        else:
            diff_text = provider.get_pr_diff(pr_number)
    except (NotImplementedError, Exception):
        logger.debug("PR diff unavailable for PR #%d", pr_number)

    lock_holder = lock_status.holder if lock_status.is_locked and not lock_status.is_stale else ""
    if current_lock_token and lock_holder == current_lock_token:
        lock_holder = ""

    # 8. Detect repair-satisfied marker in Copilot-authored issue comments
    has_repair_satisfied_marker = False
    repair_satisfied_review_id: int | None = None
    matched: list[tuple[str, int, int]] = []
    for c in issue_comments:
        if c.author in COPILOT_COMMENT_LOGINS and REPAIR_SATISFIED_MARKER in c.body:
            match = REVIEW_ID_MARKER_RE.search(c.body)
            if match:
                matched.append((c.created_at, c.id, int(match.group(1))))
    if matched:
        _created_at, _id, matched_review_id = max(matched, key=lambda item: (item[0], item[1]))
        has_repair_satisfied_marker = True
        repair_satisfied_review_id = matched_review_id

    # If active Copilot review cannot be derived from list_reviews(), fall back to the
    # review-id encoded in the repair-satisfied marker so thread state can still be loaded.
    if not review_id and repair_satisfied_review_id:
        review_id = repair_satisfied_review_id
        threads = _load_review_threads(review_id)

    return PostAgentSnapshot(
        pr_number=pr_number,
        repo=repo,
        has_sentinel=has_sentinel,
        head_changed_since_review=head_changed,
        threads=tuple(threads),
        latest_agent_comment=latest_agent_comment,
        review_id=review_id,
        review_commit_sha=review_commit_sha,
        current_head_sha=current_head_sha,
        lock_holder=lock_holder,
        lock_age_seconds=lock_status.age_seconds,
        diff_text=diff_text,
        has_repair_satisfied_marker=has_repair_satisfied_marker,
        repair_satisfied_review_id=repair_satisfied_review_id,
    )
