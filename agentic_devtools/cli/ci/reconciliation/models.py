"""Data models for the reconciliation engine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class WorkflowRun:
    """Represents a single workflow run from the CI platform.

    Attributes:
        id: Unique run identifier.
        name: Workflow name.
        conclusion: Run conclusion (e.g., "failure", "cancelled").
        run_attempt: Current attempt number for this run.
        created_at: ISO 8601 timestamp of run creation.
        event: Event that triggered the run (e.g., "push", "issue_comment").
        head_branch: Branch the run executed on.
        html_url: URL to the run in the CI platform UI.
        triggering_actor: Login of the user/actor that triggered the run.
        repository_full_name: Full "owner/repo" name.
    """

    id: int
    name: str
    conclusion: str
    run_attempt: int
    created_at: str
    event: str
    head_branch: str
    html_url: str = ""
    triggering_actor: str = ""
    repository_full_name: str = ""
    #: Explicit PR number from the API ``pull_requests[].number`` field (0 if absent).
    pr_number: int = 0


class ReconciliationAction(str, Enum):
    """Possible outcomes of a reconciliation invocation."""

    RETRIED = "retried"
    ESCALATED = "escalated"
    NO_ACTION = "no_action"


@dataclass(frozen=True)
class ReconciliationResult:
    """Result of a reconciliation engine invocation.

    Attributes:
        action: What the engine did (retried, escalated, or no_action).
        run: The workflow run that was acted upon (None if no_action).
        message: Human-readable summary of the result.
        context: Event context resolved for status reporting (None if unmappable).
    """

    action: ReconciliationAction
    run: WorkflowRun | None = None
    message: str = ""
    context: RunEventContext | None = None


@dataclass(frozen=True)
class RunEventContext:
    """Resolved context for a workflow run, mapping it to a target entity.

    Attributes:
        target_type: Type of the target ("issue", "pull_request", or "branch").
        target_id: Numeric ID for issue/PR targets, 0 for branch targets.
        branch: Branch name when target_type is "branch".
        repository_full_name: Full "owner/repo" name.
    """

    target_type: str
    target_id: int = 0
    branch: str = ""
    repository_full_name: str = ""
