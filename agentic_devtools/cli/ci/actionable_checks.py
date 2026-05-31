"""Shared actionable check names for CI evaluation."""

from __future__ import annotations

DEFAULT_ACTIONABLE_CHECK_NAMES = frozenset(
    {
        "Run Targeted Checks",
        "Run Smart Module Tests",
        "Workflow Tests",
        "Code scanning results / CodeQL",
        "CodeQL / Analyze (actions) (dynamic)",
        "CodeQL / Analyze (python) (dynamic)",
    }
)
