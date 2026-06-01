"""Base protocol for pipeline actions."""

from __future__ import annotations

from typing import Protocol

from agentic_devtools.cli.ci.pipeline.models import ActionResult
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot
from agentic_devtools.cli.ci.provider import CIPlatformProvider


class Action(Protocol):
    """Protocol that all pipeline actions must implement."""

    @property
    def name(self) -> str:
        """Human-readable name of the action."""
        ...

    def evaluate(self, snapshot: PRStateSnapshot, derived: DerivedState) -> ActionResult:
        """Evaluate preconditions and decide whether to execute.

        Returns an ActionResult with decision EXECUTE, SKIP, or BLOCKED.
        """
        ...

    def execute(
        self,
        provider: CIPlatformProvider,
        snapshot: PRStateSnapshot,
        derived: DerivedState,
    ) -> ActionResult:
        """Execute the action.

        Only called when evaluate() returns EXECUTE.
        Returns an ActionResult with decision EXECUTE, SKIP, or FAILED.
        SKIP may be returned when the provider intentionally cannot perform
        the action at runtime (e.g., missing approver token for ApproveAction).
        """
        ...
