"""Post-agent evaluator data models.

Frozen dataclasses and enums representing the PR state after a Copilot agent
session, the classification of that state, and the result of remediation actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class ThreadInfo:
    """Information about a single PR review thread.

    Attributes:
        comment_id: Database ID of the root comment in the thread.
        path: File path the thread is anchored to (empty for PR-level).
        start_line: Start line number (None for PR-level comments).
        end_line: End line number (None for PR-level comments).
        is_resolved: Whether the thread has been resolved.
        has_reply: Whether the thread has received a reply.
        body: Body text of the root comment.
    """

    comment_id: int
    path: str = ""
    start_line: int | None = None
    end_line: int | None = None
    is_resolved: bool = False
    has_reply: bool = False
    body: str = ""


@dataclass(frozen=True)
class CommentInfo:
    """Information about a PR comment (issue comment, not review comment).

    Attributes:
        id: Comment ID.
        author: Login of the comment author.
        body: Full comment body text.
        created_at: ISO 8601 timestamp.
    """

    id: int
    author: str = ""
    body: str = ""
    created_at: str = ""


@dataclass(frozen=True)
class PostAgentSnapshot:
    """Immutable snapshot of PR state after a Copilot agent session.

    This dataclass captures all relevant PR metadata needed for
    classification by ``classify_post_agent_state()``.

    Attributes:
        pr_number: Pull request number.
        repo: Full repository name (owner/repo).
        has_sentinel: Whether the sentinel marker comment exists.
        head_changed_since_review: Whether HEAD SHA differs from the review commit.
        threads: List of review thread info objects.
        latest_agent_comment: The most recent Copilot agent comment (if any).
        review_id: ID of the Copilot review being evaluated.
        review_commit_sha: Commit SHA that the review targets.
        current_head_sha: Current HEAD SHA of the PR.
        lock_holder: Token of the current lock holder (empty if unlocked).
        lock_age_seconds: Age of the lock in seconds (0 if unlocked).
        diff_text: Unified diff text of the PR (empty if unavailable).
    """

    pr_number: int
    repo: str = ""
    has_sentinel: bool = False
    head_changed_since_review: bool = False
    threads: tuple[ThreadInfo, ...] = ()
    latest_agent_comment: CommentInfo | None = None
    review_id: int = 0
    review_commit_sha: str = ""
    current_head_sha: str = ""
    lock_holder: str = ""
    lock_age_seconds: float = 0.0
    diff_text: str = ""
    has_repair_satisfied_marker: bool = False
    repair_satisfied_review_id: int | None = None


class PostAgentClassification(Enum):
    """Classification of the post-agent PR state.

    Each variant maps to a specific remediation path.
    """

    complete = "complete"
    repair_satisfied_no_changes = "repair_satisfied_no_changes"
    agent_claims_fixed_no_sentinel = "agent_claims_fixed_no_sentinel"
    threads_resolved_no_sentinel = "threads_resolved_no_sentinel"
    changes_made_threads_unresolved = "changes_made_threads_unresolved"
    agent_silent = "agent_silent"
    concurrent_evaluation_skipped = "concurrent_evaluation_skipped"


class PostAgentAction(Enum):
    """Action to take based on the classification."""

    no_action = "no_action"
    resolve_evaluated_threads = "resolve_evaluated_threads"
    verify_and_resolve = "verify_and_resolve"
    synthesize_sentinel = "synthesize_sentinel"
    trigger_re_review = "trigger_re_review"
    agentic_fallback = "agentic_fallback"


@dataclass(frozen=True)
class EvaluationResult:
    """Result of the post-agent evaluation and remediation.

    Attributes:
        classification: The determined classification.
        action_taken: The action that was executed.
        success: Whether the action completed successfully.
        threads_resolved: Number of threads resolved.
        threads_unresolved: Number of threads still unresolved.
        error_details: Error description if action failed (None on success).
        dry_run: Whether this was a dry-run execution.
    """

    classification: PostAgentClassification
    action_taken: PostAgentAction
    success: bool = True
    threads_resolved: int = 0
    threads_unresolved: int = 0
    error_details: str | None = None
    dry_run: bool = False

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "classification": self.classification.value,
            "action_taken": self.action_taken.value,
            "success": self.success,
            "threads_resolved": self.threads_resolved,
            "threads_unresolved": self.threads_unresolved,
            "error_details": self.error_details,
            "dry_run": self.dry_run,
        }
