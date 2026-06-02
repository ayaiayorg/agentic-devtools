"""SpecKit trigger orchestration — DEPRECATED.

This module previously handled Phase 1 (Specify) orchestration for issues
label events. The logic has been consolidated into the unified
``speckit-phase-progression.yml`` workflow which handles all phases 1–5.

The ``speckit-issue-trigger.yml`` workflow is now a thin dispatcher that
triggers ``speckit-phase-progression.yml`` via ``workflow_dispatch``.

See: https://github.com/ayaiayorg/agentic-devtools/issues/1527
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

EXIT_SUCCESS = 0
EXIT_FAILED = 1
EXIT_MALFORMED_EVENT = 2
EXIT_MISSING_CONFIG = 10

DEPRECATION_MESSAGE = (
    "agdt-speckit-trigger is deprecated. "
    "Phase 1 is now handled by speckit-phase-progression.yml. "
    "Use workflow_dispatch with phase=1 on speckit-phase-progression.yml instead."
)

_DEPRECATION_MESSAGE = DEPRECATION_MESSAGE
