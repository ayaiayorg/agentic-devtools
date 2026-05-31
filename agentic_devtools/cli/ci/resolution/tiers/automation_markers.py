"""Tier 2: Automation marker pattern match.

Resolves threads where the most recent comment body contains a known
automation marker (e.g., "autofix applied"), indicating that a tool
has already addressed the review comment.
"""

from __future__ import annotations

import logging
import re

from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, TierResult
from agentic_devtools.cli.ci.resolution.protocols import ResolutionContext, ReviewThread

logger = logging.getLogger(__name__)

# Hardcoded automation markers — case-insensitive substring match.
# Extension point: future iterations can load overrides from config.
AUTOMATION_MARKERS: list[str] = [
    "autofix applied",
    "suggestion applied",
    "fix applied",
]

_NEGATED_PREFIX_RE = re.compile(r"\b(?:no|not|never)\s+$")
_NEGATIVE_SUFFIX_RE = re.compile(r"^[\s\W]*(?:failed?|fails|failing|unsuccessful|unsuccessfully|error|errored)\b")


def _is_positive_marker_match(body: str, marker: str) -> bool:
    """Return True when marker appears in an explicitly positive context."""
    marker_re = re.compile(rf"\b{re.escape(marker)}\b")
    for match in marker_re.finditer(body):
        prefix = body[max(0, match.start() - 25) : match.start()]
        suffix = body[match.end() : match.end() + 30]

        if _NEGATED_PREFIX_RE.search(prefix):
            continue
        if _NEGATIVE_SUFFIX_RE.search(suffix):
            continue

        return True
    return False


class AutomationMarkerTier:
    """Tier 2: Resolve threads with automation marker in most recent comment."""

    @property
    def name(self) -> str:
        return "automation_marker"

    def evaluate(self, thread: ReviewThread, context: ResolutionContext) -> TierResult | None:
        """Return RESOLVE if the most recent comment contains an automation marker."""
        if not thread.comments:
            return None

        most_recent_body = thread.comments[-1].body.lower()
        snippet = most_recent_body[:100]
        logger.debug(
            "Thread %s: evaluating automation_marker tier (snippet=%r)",
            thread.thread_id,
            snippet,
        )

        for marker in AUTOMATION_MARKERS:
            if _is_positive_marker_match(most_recent_body, marker):
                return TierResult(
                    verdict=ResolutionVerdict.RESOLVE,
                    confidence="high",
                    tier_name=self.name,
                    explanation=f'Automation marker "{marker}" detected in most recent comment.',
                )

        return None
