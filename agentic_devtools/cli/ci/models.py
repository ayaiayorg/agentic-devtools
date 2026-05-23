"""CI provider data models.

Dataclasses representing normalized CI platform events and metadata.
These are provider-agnostic — each provider's ``parse_event()`` method
normalizes platform-specific payloads into these structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


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
# All Copilot identities that may leave comments (superset of COPILOT_LOGINS)
COPILOT_COMMENT_LOGINS = frozenset({"copilot[bot]", "Copilot", COPILOT_REVIEWER_LOGIN})


@dataclass(frozen=True)
class ReviewCommentInfo:
    """Rich metadata for a single PR review comment.

    Attributes:
        id: Database ID of the review comment.
        path: File path the comment is on.
        body: Full comment text (the reviewer's feedback).
        html_url: Direct link to the inline comment on GitHub.
        is_suppressed: Whether the comment has been minimized/suppressed on GitHub.
        start_line: Start line number the comment targets (None for file-level).
        end_line: End line number the comment targets (single-line comments set
            this to the anchor line; None only when line metadata is unavailable).
        line: Line number the comment targets (None if PR-level).
        position: Diff position the comment targets (None if PR-level).
        diff_hunk: Diff hunk context from the API (empty if not available).
    """

    id: int
    path: str
    body: str
    html_url: str
    is_suppressed: bool = False
    start_line: int | None = None
    end_line: int | None = None
    line: int | None = None
    position: int | None = None
    diff_hunk: str = ""


@dataclass(frozen=True)
class IssueCommentInfo:
    """Metadata for a pull request issue comment.

    Attributes:
        id: Database ID of the issue comment.
        author: Login of the comment author.
        body: Full comment body text.
        created_at: ISO 8601 creation timestamp.
    """

    id: int
    author: str
    body: str = ""
    created_at: str = ""


# Copilot session event type strings from the GitHub Issues Events API
COPILOT_SESSION_EVENT_FINISHED = "copilot_work_finished"
COPILOT_SESSION_EVENT_FINISHED_FAILURE = "copilot_work_finished_failure"
COPILOT_SESSION_EVENT_STARTED = "copilot_work_started"

_COPILOT_SESSION_EVENTS = frozenset(
    {
        COPILOT_SESSION_EVENT_FINISHED,
        COPILOT_SESSION_EVENT_FINISHED_FAILURE,
        COPILOT_SESSION_EVENT_STARTED,
    }
)


@dataclass(frozen=True)
class IssueEvent:
    """A single issue/PR timeline event from the GitHub Issues Events API.

    Attributes:
        id: Event ID.
        event: Event type string (e.g., "copilot_work_finished",
               "copilot_work_finished_failure", "copilot_work_started").
        created_at: ISO 8601 timestamp string when the event was created.
        actor_login: Login of the actor who triggered the event (empty if unknown).
    """

    id: int
    event: str
    created_at: str
    actor_login: str = ""


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


class VerificationVerdict(Enum):
    """Verdict from the SDK verification of a review comment against the diff.

    Attributes:
        COMMENT_RESOLVE: The comment has been addressed by the diff.
        COMMENT_UNRESOLVE: The comment has NOT been addressed by the diff.
    """

    COMMENT_RESOLVE = "COMMENT_RESOLVE"
    COMMENT_UNRESOLVE = "COMMENT_UNRESOLVE"


@dataclass(frozen=True)
class CommentResolution:
    """Resolution result for a single review comment.

    Attributes:
        comment_id: Database ID of the review comment.
        thread_id: Thread/node ID for GraphQL resolution (empty if unknown).
        verdict: SDK verdict for this comment.
        error: Error message if SDK call failed (empty on success).
    """

    comment_id: int
    thread_id: str = ""
    verdict: VerificationVerdict = VerificationVerdict.COMMENT_UNRESOLVE
    error: str = ""


@dataclass(frozen=True)
class FinalizationResult:
    """Result of the post-repair finalization process.

    Attributes:
        skipped: Whether finalization was skipped entirely (e.g., no new commit).
        reason: Human-readable reason when skipped or for summary purposes.
        resolved_count: Number of comments resolved.
        unresolved_count: Number of comments left unresolved.
        resolutions: Individual resolution results per comment.
        errors: List of error messages encountered during finalization.
    """

    skipped: bool = False
    reason: str = ""
    resolved_count: int = 0
    unresolved_count: int = 0
    resolutions: tuple[CommentResolution, ...] = ()
    errors: tuple[str, ...] = ()
