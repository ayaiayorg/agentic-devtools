"""CI provider data models.

Dataclasses representing normalized CI platform events and metadata.
These are provider-agnostic — each provider's ``parse_event()`` method
normalizes platform-specific payloads into these structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EventPayload:
    """Normalized CI event payload.

    Attributes:
        pr_number: Pull request number (0 if not a PR event).
        head_branch: Head branch name.
        head_sha: HEAD commit SHA.
        base_branch: Base/target branch name.
        action: Event action (e.g., "opened", "synchronize", "submitted").
        trigger_label: Label name that triggered the event (empty if not a label event).
        repository_full_name: Full repository name (e.g., "owner/repo").
        sender_login: Login of the event sender/actor, when available.
    """

    pr_number: int = 0
    head_branch: str = ""
    head_sha: str = ""
    base_branch: str = ""
    action: str = ""
    trigger_label: str = ""
    repository_full_name: str = ""
    sender_login: str = ""


@dataclass(frozen=True)
class PRMetadata:
    """Pull request metadata retrieved from the CI platform.

    Attributes:
        number: PR number.
        title: PR title.
        head_branch: Source branch name.
        head_sha: HEAD commit SHA.
        base_branch: Target branch name.
        head_repo_full_name: Full name of the head (source) repository.
        base_repo_full_name: Full name of the base (target) repository.
        labels: List of label names on the PR.
        requested_reviewers: List of pending reviewer logins on the PR.
        is_draft: Whether the PR is a draft.
        mergeable: Whether the PR is mergeable (None if unknown).
    """

    number: int
    title: str
    head_branch: str
    head_sha: str
    base_branch: str
    head_repo_full_name: str = ""
    base_repo_full_name: str = ""
    labels: list[str] = field(default_factory=list)
    requested_reviewers: list[str] = field(default_factory=list)
    is_draft: bool = False
    mergeable: bool | None = None


@dataclass(frozen=True)
class CheckRunStatus:
    """Status of a single CI check run.

    Attributes:
        id: Check run ID.
        name: Check run name.
        status: Run status (e.g., "completed", "in_progress", "queued").
        conclusion: Run conclusion (e.g., "success", "failure", "neutral").
            Empty string if not yet completed.
        html_url: Direct HTML URL to view this check run in the GitHub UI.
            Prefer this over constructing a URL from ``id``, since the check
            run ID does not match the Actions workflow run ID.
            Empty string when not available.
    """

    id: int
    name: str
    status: str
    conclusion: str = ""
    html_url: str = ""


@dataclass(frozen=True)
class ReviewInfo:
    """Information about a pull request review.

    Attributes:
        id: Review ID.
        user: Username of the reviewer.
        state: Review state (e.g., "APPROVED", "CHANGES_REQUESTED", "COMMENTED").
        body: Review body text.
        commit_sha: Commit SHA that this review targets.
    """

    id: int
    user: str
    state: str
    body: str = ""
    commit_sha: str = ""


# Copilot login names used in review detection (provider-agnostic)
COPILOT_REVIEWER_LOGIN = "copilot-pull-request-reviewer[bot]"
COPILOT_LOGINS = frozenset({"Copilot", COPILOT_REVIEWER_LOGIN})


@dataclass(frozen=True)
class ReviewCommentInfo:
    """Rich metadata for a single PR review comment.

    Attributes:
        id: Database ID of the review comment.
        path: File path the comment is on.
        body: Full comment text (the reviewer's feedback).
        html_url: Direct link to the inline comment on GitHub.
        is_suppressed: Whether the comment has been minimized/suppressed on GitHub.
    """

    id: int
    path: str
    body: str
    html_url: str
    is_suppressed: bool = False


@dataclass(frozen=True)
class RepairDecision:
    """Result of the dispatch decision for repair.

    Attributes:
        repair_needed: Whether a repair dispatch should be triggered.
        repair_type: Type of repair needed: ``"review"``, ``"ci"``, or ``"both"``.
            Empty string when no repair is needed.
        review_id: ID of the actionable Copilot review (CHANGES_REQUESTED or
            COMMENTED with inline comments; 0 if N/A).
        review_comments: Rich review comment metadata pre-fetched during detection
            (populated for COMMENTED reviews; empty for CHANGES_REQUESTED so
            that ``_dispatch_repair`` fetches them lazily).
        failed_checks: Failed check run details (name, status, conclusion).
    """

    repair_needed: bool = False
    repair_type: str = ""
    review_id: int = 0
    review_comments: tuple[ReviewCommentInfo, ...] = ()
    failed_checks: tuple[CheckRunStatus, ...] = ()
