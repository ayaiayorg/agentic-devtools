"""Configuration constants for the reconciliation engine.

All values are overridable via environment variables.
"""

from __future__ import annotations

import os


def _safe_int(env_var: str, default: int, min_value: int = 1) -> int:
    """Return the integer value of *env_var*, falling back to *default*.

    If the environment variable is set but cannot be parsed as an integer,
    or its value is below *min_value*, the default value is returned silently
    so that importing this module never raises at import time.
    """
    raw = os.environ.get(env_var)
    if raw is None:
        return default
    try:
        value = int(raw)
        return value if value >= min_value else default
    except ValueError:
        return default


#: Maximum number of retry attempts per workflow run (default: 3).
#: Override with ``AGDT_MAX_RUN_ATTEMPTS`` env var.
MAX_RUN_ATTEMPTS: int = _safe_int("AGDT_MAX_RUN_ATTEMPTS", 3)

#: Time window in hours to look back for retriable runs (default: 24).
#: Override with ``AGDT_RECONCILIATION_WINDOW_HOURS`` env var.
RECONCILIATION_WINDOW_HOURS: int = _safe_int("AGDT_RECONCILIATION_WINDOW_HOURS", 24)

#: Workflow run conclusions eligible for retry.
RETRIABLE_CONCLUSIONS: frozenset[str] = frozenset({"cancelled", "failure", "timed_out", "startup_failure"})
