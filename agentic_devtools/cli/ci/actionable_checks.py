"""Shared actionable check names for CI evaluation."""

from __future__ import annotations

DEFAULT_ACTIONABLE_CHECK_NAMES = frozenset(
    {
        "Targeted Checks ✅",
        "Smart Module Tests ✅",
        "Copilot Review ✅",
        "Workflow Tests ✅",
        "Code scanning results / CodeQL",
    }
)
