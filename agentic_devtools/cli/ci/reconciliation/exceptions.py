"""Exceptions for the reconciliation engine."""

from __future__ import annotations


class UnmappableContextError(Exception):
    """Raised when a workflow run's event context cannot be mapped to a target.

    This prevents the engine from guessing and posting escalation to the
    wrong target.

    Attributes:
        run_id: The workflow run ID that could not be mapped.
        event: The event type that was unresolvable.
    """

    def __init__(self, run_id: int, event: str, detail: str = "") -> None:
        self.run_id = run_id
        self.event = event
        msg = f"Cannot map run {run_id} (event={event!r}) to a target"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)
