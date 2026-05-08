"""Finalization pass for PR review workflow.

Automatically verifies, repairs, and finalizes AGDT-generated PR review
comments during the workflow completion step.
"""

from .models import FinalizationReport
from .orchestrator import run_finalization_pass

__all__ = ["run_finalization_pass", "FinalizationReport"]
