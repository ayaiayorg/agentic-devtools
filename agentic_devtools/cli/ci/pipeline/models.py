"""Core data models for the idempotent action pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentic_devtools.cli.ci.pipeline.snapshot import PRStateSnapshot


class ActionDecision(Enum):
    """Outcome of evaluating an action's preconditions."""

    EXECUTE = "execute"
    SKIP = "skip"
    BLOCKED = "blocked"
    BLOCKED_BY_GUARD = "blocked_by_guard"
    FAILED = "failed"


@dataclass
class ActionResult:
    """Result of a single action evaluation and optional execution.

    Attributes:
        name: Action name (e.g., "guards", "publish", "merge").
        decision: The evaluation outcome.
        preconditions: Dict of precondition name to boolean result.
        details: Human-readable details about the decision or execution.
        error: Error message if the action failed.
        limit_reached: True when dispatch_repair was skipped because a
            deduplication or cycle limit was hit.  Used by
            ``_determine_exit_code`` to return EXIT_GUARD_BLOCKED without
            relying on free-form text matching.
        invalidates_snapshot: True when the action changes PR HEAD and the
            remaining pipeline decisions must wait for a fresh snapshot on the
            next run.
    """

    name: str
    decision: ActionDecision
    preconditions: dict[str, bool] = field(default_factory=dict)
    details: str = ""
    error: str = ""
    limit_reached: bool = False
    invalidates_snapshot: bool = False


@dataclass
class PipelineRunSummary:
    """Summary of a complete pipeline run.

    Attributes:
        results: Ordered list of action results.
        snapshot: The PR state snapshot used for this run.
        run_url: URL to the GitHub Actions workflow run.
        timestamp: ISO 8601 timestamp of the run.
        trigger_reason: Human-readable reason why this pipeline run was triggered.
    """

    results: list[ActionResult] = field(default_factory=list)
    snapshot: PRStateSnapshot | None = None
    run_url: str = ""
    timestamp: str = ""
    trigger_reason: str = ""
