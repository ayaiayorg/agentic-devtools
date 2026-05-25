"""Idempotent action pipeline for the AI PR loop.

Replaces the event-branching orchestrator with a sequential pipeline of
action evaluators, each self-contained with precondition checks and
idempotent execution.
"""

from agentic_devtools.cli.ci.pipeline.models import (
    ActionDecision,
    ActionResult,
    PipelineRunSummary,
)
from agentic_devtools.cli.ci.pipeline.runner import run_pipeline
from agentic_devtools.cli.ci.pipeline.snapshot import (
    DerivedState,
    PRStateSnapshot,
    build_pr_state_snapshot,
)

__all__ = [
    "ActionDecision",
    "ActionResult",
    "DerivedState",
    "PRStateSnapshot",
    "PipelineRunSummary",
    "build_pr_state_snapshot",
    "run_pipeline",
]
