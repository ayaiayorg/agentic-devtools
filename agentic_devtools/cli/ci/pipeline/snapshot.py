"""PR state snapshot and derived state for the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agentic_devtools.cli.ci.actionable_checks import DEFAULT_ACTIONABLE_CHECK_NAMES
from agentic_devtools.cli.ci.models import (
    COPILOT_LOGINS,
    CheckRunStatus,
    ReviewInfo,
)
from agentic_devtools.cli.ci.provider import CIPlatformProvider


@dataclass(frozen=True)
class PRStateSnapshot:
    """Immutable snapshot of all PR state gathered in one pass.

    Attributes:
        pr_number: The pull request number.
        head_sha: Current HEAD commit SHA.
        base_branch: Target branch name.
        head_branch: Source branch name.
        commit_count: Number of commits above merge-base.
        ci_status: Overall CI status ("passing", "failing", "pending", "unknown").
        ci_failed_checks: List of failed check run names.
        review_state: Latest Copilot review state on HEAD (or empty string).
        copilot_review_id: ID of the latest Copilot review on HEAD (0 if none).
        copilot_review_inline_count: Number of inline comments in the Copilot review;
            `-1` indicates the count is unknown because review comments could not be fetched.
        active_session: Whether a Copilot coding session is currently active.
        copilot_review_pending: Whether Copilot is pending as a reviewer.
        unresolved_threads: Number of unresolved Copilot review threads from prior commits.
        labels: List of labels on the PR.
        is_draft: Whether the PR is a draft.
        mergeable: Whether the PR is mergeable (None if unknown).
        requested_reviewers: List of pending reviewer logins.
        has_approval_on_head: Whether an approval exists targeting the current HEAD.
        title: PR title.
        head_repo_full_name: Full name of the head repository.
        base_repo_full_name: Full name of the base repository.
        files: List of files changed in the PR.
        check_runs: All check run statuses.
        reviews: All reviews for the PR.
        has_changes: Whether the PR has file changes.
    """

    pr_number: int = 0
    head_sha: str = ""
    base_branch: str = ""
    head_branch: str = ""
    commit_count: int = 1
    ci_status: str = "unknown"
    ci_failed_checks: list[str] = field(default_factory=list)
    review_state: str = ""
    copilot_review_id: int = 0
    copilot_review_inline_count: int = 0
    active_session: bool = False
    copilot_review_pending: bool = False
    unresolved_threads: int = 0
    labels: list[str] = field(default_factory=list)
    is_draft: bool = False
    mergeable: bool | None = None
    requested_reviewers: list[str] = field(default_factory=list)
    has_approval_on_head: bool = False
    title: str = ""
    head_repo_full_name: str = ""
    base_repo_full_name: str = ""
    files: list[str] = field(default_factory=list)
    check_runs: list[CheckRunStatus] = field(default_factory=list)
    reviews: list[ReviewInfo] = field(default_factory=list)
    has_changes: bool = False


class DerivedState:
    """Mutable proxy over PRStateSnapshot that allows pipeline actions to update state.

    Actions can mutate derived state (e.g., marking draft as published) so that
    subsequent actions see the effect without re-querying the provider.
    """

    def __init__(self, snapshot: PRStateSnapshot) -> None:
        self._snapshot = snapshot
        self._overrides: dict[str, Any] = {}

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._snapshot, name)

    def set(self, name: str, value: Any) -> None:
        """Set a derived state override."""
        self._overrides[name] = value

    @property
    def snapshot(self) -> PRStateSnapshot:
        """Access the underlying immutable snapshot."""
        return self._snapshot


_DEFAULT_ACTIONABLE_CHECK_NAMES = DEFAULT_ACTIONABLE_CHECK_NAMES


def build_pr_state_snapshot(
    provider: CIPlatformProvider,
    pr_number: int,
    *,
    actionable_check_names: frozenset[str] | None = None,
) -> PRStateSnapshot:
    """Build a complete PR state snapshot in one pass.

    Gathers all required data from the provider to make a single
    immutable snapshot that the pipeline evaluates against.
    """
    if actionable_check_names is None:
        actionable_check_names = _DEFAULT_ACTIONABLE_CHECK_NAMES

    # Get PR metadata
    pr_meta = provider.get_pr_metadata(pr_number)

    # List files — fail closed: if this raises, the caller gets EXIT_METADATA_FAILED
    # so that guards (privileged-path / Dockerfile checks) are never bypassed by a
    # missing file list.
    files = provider.list_pr_files(pr_number)

    # Get check runs — fail closed: if this raises, the caller gets EXIT_METADATA_FAILED
    # so that a provider/API outage cannot silently drive ci_status to 'pending' and
    # allow the pipeline to evaluate readiness against stale/missing data.
    check_runs = provider.list_check_runs(pr_meta.head_sha)

    # Evaluate CI status
    ci_status, ci_failed_checks = _evaluate_ci_status(check_runs, actionable_check_names)

    # Get reviews — fail closed: if this raises, the caller gets EXIT_METADATA_FAILED
    # so that review/pending-review state is never evaluated from incomplete metadata.
    reviews = provider.list_reviews(pr_number)

    # Determine effective review states on HEAD (latest review.id per reviewer;
    # all Copilot aliases are collapsed to one reviewer key).
    copilot_review_state = ""
    copilot_review_id = 0
    copilot_review_inline_count = 0
    has_approval_on_head = False

    current_head_sha = pr_meta.head_sha
    effective_head_reviews = get_effective_head_reviews(reviews, current_head_sha)
    has_approval_on_head = any(review.state == "APPROVED" for review in effective_head_reviews)

    # Find effective Copilot review on HEAD
    copilot_review = next((review for review in effective_head_reviews if review.user in COPILOT_LOGINS), None)
    if copilot_review is not None:
        copilot_review_state = copilot_review.state
        copilot_review_id = copilot_review.id
        # Count inline comments for COMMENTED reviews
        if copilot_review.state == "COMMENTED":
            try:
                comments = provider.list_review_comments(pr_number, copilot_review.id)
                copilot_review_inline_count = len(comments)
            except Exception:
                copilot_review_inline_count = -1  # unknown

    # Count unresolved threads from prior commits
    unresolved_threads = _count_unresolved_prior_threads(provider, pr_number, reviews, current_head_sha)

    # Check Copilot review pending
    copilot_review_pending = _is_copilot_review_pending(pr_meta.requested_reviewers)

    # Count commits above merge-base
    commit_count = _count_commits(provider, base_branch=pr_meta.base_branch, head_sha=pr_meta.head_sha)

    return PRStateSnapshot(
        pr_number=pr_number,
        head_sha=pr_meta.head_sha,
        base_branch=pr_meta.base_branch,
        head_branch=pr_meta.head_branch,
        commit_count=commit_count,
        ci_status=ci_status,
        ci_failed_checks=ci_failed_checks,
        review_state=copilot_review_state,
        copilot_review_id=copilot_review_id,
        copilot_review_inline_count=copilot_review_inline_count,
        copilot_review_pending=copilot_review_pending,
        unresolved_threads=unresolved_threads,
        labels=list(pr_meta.labels),
        is_draft=pr_meta.is_draft,
        mergeable=pr_meta.mergeable,
        requested_reviewers=list(pr_meta.requested_reviewers),
        has_approval_on_head=has_approval_on_head,
        title=pr_meta.title,
        head_repo_full_name=pr_meta.head_repo_full_name,
        base_repo_full_name=pr_meta.base_repo_full_name,
        files=files,
        check_runs=check_runs,
        reviews=reviews,
        has_changes=bool(files),
    )


def _evaluate_ci_status(
    check_runs: list[CheckRunStatus],
    actionable_check_names: frozenset[str],
) -> tuple[str, list[str]]:
    """Evaluate CI status from check runs.

    Returns:
        Tuple of (status_string, list_of_failed_check_names).
    """
    any_failed = False
    any_pending = False
    any_unknown = False
    failed_checks: list[str] = []
    actionable_seen = 0

    for cr in check_runs:
        if cr.name not in actionable_check_names:
            continue
        actionable_seen += 1
        if cr.status != "completed":
            any_pending = True
        elif cr.conclusion == "failure":
            any_failed = True
            failed_checks.append(cr.name)
        elif cr.conclusion not in ("success", "neutral", "skipped"):
            any_unknown = True

    if actionable_seen == 0:
        return "pending", []
    if any_pending:
        return "pending", failed_checks
    if any_failed:
        return "failing", failed_checks
    if any_unknown:
        return "unknown", failed_checks
    return "passing", []


def _is_copilot_review_pending(requested_reviewers: list[str]) -> bool:
    """Return True when Copilot is currently requested as a pending reviewer."""
    copilot_logins = {login.casefold() for login in COPILOT_LOGINS}
    return any(reviewer.casefold() in copilot_logins for reviewer in requested_reviewers)


def _count_unresolved_prior_threads(
    provider: CIPlatformProvider,
    pr_number: int,
    reviews: list[ReviewInfo],
    current_head_sha: str,
) -> int:
    """Count unresolved Copilot review threads from commits before HEAD.

    Returns the count of review comments from prior-commit Copilot reviews
    whose threads are actually unresolved per the GitHub API. If thread-state
    data is unavailable, falls back to counting all non-synthetic comments.
    """
    prior_copilot_reviews = [
        r
        for r in reviews
        if r.user in COPILOT_LOGINS
        and r.commit_sha
        and r.commit_sha != current_head_sha
        and r.state in ("CHANGES_REQUESTED", "COMMENTED")
    ]
    if not prior_copilot_reviews:
        return 0

    # Fetch actual thread resolution states from GitHub GraphQL API
    thread_statuses: dict[int, tuple[bool, bool]] | None = None
    list_thread_states = getattr(provider, "list_review_thread_states", None)
    if callable(list_thread_states):
        try:
            thread_statuses = list_thread_states(pr_number)
        except Exception:
            # Fail closed: if we can't determine resolution status, fall
            # through to counting all comments (existing behavior).
            thread_statuses = None

    # Count only comments whose thread is NOT resolved (when status is known)
    total_unresolved = 0
    for prior_review in prior_copilot_reviews:
        try:
            comments = provider.list_review_comments(pr_number, prior_review.id)
            for c in comments:
                if c.id < 0:
                    continue  # Skip synthetic review-body entries
                if thread_statuses is not None:
                    is_resolved, _has_reply = thread_statuses.get(c.id, (False, False))
                    if not is_resolved:
                        total_unresolved += 1
                else:
                    # Fallback: no thread status info, count all
                    total_unresolved += 1
        except Exception:
            # Fail closed for this review: count 1 unknown thread
            total_unresolved += 1
    return total_unresolved


def _count_commits(provider: CIPlatformProvider, *, base_branch: str, head_sha: str) -> int:
    """Return commit count above merge-base, or 1 when the provider lacks support.

    Raises:
        Exception: Propagated from the provider when commit counting is supported
            but fails. The caller should treat this as a metadata failure so the
            pipeline does not proceed with an unknown commit count.
    """
    counter = getattr(provider, "count_commits_above_merge_base", None)
    if not callable(counter):
        return 1
    count = counter(base_branch=base_branch, head_sha=head_sha)
    return int(count)


def get_effective_head_reviews(reviews: list[ReviewInfo], current_head_sha: str) -> list[ReviewInfo]:
    """Return latest effective reviews on HEAD (latest review.id per reviewer).

    All Copilot aliases are normalized to a single reviewer key so a newer
    Copilot review supersedes older Copilot reviews across aliases.
    """
    latest_by_user: dict[str, ReviewInfo] = {}
    for review in reviews:
        if review.commit_sha and review.commit_sha != current_head_sha:
            continue
        user_key = "copilot" if review.user in COPILOT_LOGINS else review.user
        existing = latest_by_user.get(user_key)
        if existing is None or review.id > existing.id:
            latest_by_user[user_key] = review
    return list(latest_by_user.values())


def has_non_copilot_changes_requested_on_head(reviews: list[ReviewInfo], current_head_sha: str) -> bool:
    """Return True when any non-Copilot effective HEAD review requests changes."""
    return any(
        review.user not in COPILOT_LOGINS and review.state == "CHANGES_REQUESTED"
        for review in get_effective_head_reviews(reviews, current_head_sha)
    )
