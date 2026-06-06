"""Tier: Thread-evaluated marker resolution.

Resolves threads where the Copilot agent has replied with the
``<!-- ai-pr-loop:thread-evaluated -->`` marker, indicating that the thread
was individually evaluated and no code change is warranted.

This tier provides HIGH confidence resolution for the no-commit-needed flow,
allowing the orchestrator to resolve threads without SDK verification.
"""

from __future__ import annotations

import logging

from agentic_devtools.cli.ci.guards import THREAD_EVALUATED_MARKER
from agentic_devtools.cli.ci.models import COPILOT_COMMENT_LOGINS
from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, TierResult
from agentic_devtools.cli.ci.resolution.protocols import ResolutionContext, ReviewThread

logger = logging.getLogger(__name__)


class ThreadEvaluatedTier:
    """Resolve threads with a thread-evaluated marker from an authorized identity.

    Checks the most recent comment in the thread for the
    ``<!-- ai-pr-loop:thread-evaluated -->`` marker. If found from an authorized
    Copilot identity, returns HIGH confidence RESOLVE. If the marker is from an
    unauthorized user or absent, returns None to fall through to the next tier.
    """

    @property
    def name(self) -> str:
        return "thread_evaluated"

    def evaluate(self, thread: ReviewThread, context: ResolutionContext) -> TierResult | None:
        """Return RESOLVE (high) if the most recent comment has a thread-evaluated marker from authorized identity."""
        if not thread.comments:
            return None
        most_recent = thread.comments[-1]
        if THREAD_EVALUATED_MARKER in most_recent.body:
            author = most_recent.author_login
            if author in COPILOT_COMMENT_LOGINS:
                logger.debug(
                    "Thread %s: thread-evaluated marker from %r — resolving",
                    thread.thread_id,
                    author,
                )
                return TierResult(
                    verdict=ResolutionVerdict.RESOLVE,
                    confidence="high",
                    tier_name=self.name,
                    explanation="Thread evaluated by agent — no code change needed.",
                )
            else:
                logger.debug(
                    "Thread %s: thread-evaluated marker from unauthorized user %r — ignoring",
                    thread.thread_id,
                    author,
                )
        return None
