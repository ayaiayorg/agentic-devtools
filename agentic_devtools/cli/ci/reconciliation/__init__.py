"""SpecKit pipeline retry & reconciliation logic.

Provides a reusable, provider-abstracted reconciliation engine that retries
failed workflow runs and escalates when retry limits are reached.
"""

from agentic_devtools.cli.ci.reconciliation.config import (
    MAX_RUN_ATTEMPTS,
    RECONCILIATION_WINDOW_HOURS,
    RETRIABLE_CONCLUSIONS,
)
from agentic_devtools.cli.ci.reconciliation.engine import reconcile
from agentic_devtools.cli.ci.reconciliation.exceptions import UnmappableContextError
from agentic_devtools.cli.ci.reconciliation.models import (
    ReconciliationAction,
    ReconciliationResult,
    RunEventContext,
    WorkflowRun,
)

__all__ = [
    "MAX_RUN_ATTEMPTS",
    "RECONCILIATION_WINDOW_HOURS",
    "RETRIABLE_CONCLUSIONS",
    "ReconciliationAction",
    "ReconciliationResult",
    "RunEventContext",
    "UnmappableContextError",
    "WorkflowRun",
    "reconcile",
]
