"""Tier 1: isOutdated resolution.

Resolves threads that GitHub has marked as outdated without invoking
the SDK. This is the strongest programmatic signal — GitHub sets
isOutdated when the underlying code at the commented file/line has
changed since the comment was posted.
"""

from __future__ import annotations

import logging

from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, TierResult
from agentic_devtools.cli.ci.resolution.protocols import ResolutionContext, ReviewThread

logger = logging.getLogger(__name__)


class OutdatedTier:
    """Tier 1: Resolve threads marked as outdated by the platform."""

    @property
    def name(self) -> str:
        return "outdated"

    def evaluate(self, thread: ReviewThread, context: ResolutionContext) -> TierResult | None:
        """Return RESOLVE if isOutdated is True, None otherwise."""
        logger.debug(
            "Thread %s: evaluating outdated tier (is_outdated=%s)",
            thread.thread_id,
            thread.is_outdated,
        )
        if thread.is_outdated is True:
            return TierResult(
                verdict=ResolutionVerdict.RESOLVE,
                confidence="high",
                tier_name=self.name,
                explanation="Thread is marked as outdated by the platform — the commented code has been modified.",
            )
        return None
