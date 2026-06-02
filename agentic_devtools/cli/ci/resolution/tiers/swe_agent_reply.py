"""Tier 2.5: SWE agent reply resolution.

Resolves threads where the Copilot SWE agent has directly replied in the thread
(Scenario A) or where a Copilot work session started after the review and the
SWE agent posted a comment on the PR (Scenario B).

Both scenarios indicate that the agent was actively working to address the review
feedback, making high-confidence resolution appropriate when HEAD has changed.
"""

from __future__ import annotations

import logging

from agentic_devtools.cli.ci.models import COPILOT_COMMENT_LOGINS
from agentic_devtools.cli.ci.resolution.protocols import ResolutionContext, ReviewThread

logger = logging.getLogger(__name__)


class SweAgentReplyTier:
    """Tier 2.5: Resolve threads where the SWE agent has addressed the feedback.

    Handles two scenarios:
    - Scenario A: The last comment in the thread was posted by a known SWE agent
      bot login (e.g., ``"Copilot"``).
    - Scenario B: A Copilot work session started after the review comment was
      created AND the SWE agent has left a reply on the PR. Both signals together
      provide high confidence that the agent was dispatched to address this review
      and engaged with it.
    """

    @property
    def name(self) -> str:
        return "swe_agent_reply"

    def evaluate(self, thread: ReviewThread, context: ResolutionContext) -> TierResult | None:
        """Return RESOLVE (high) if the SWE agent has addressed the thread.

        Checks Scenario A first (direct thread reply), then Scenario B
        (session started after review + agent commented on PR).
        """
            if author in COPILOT_COMMENT_LOGINS:
                    "Thread %s: SWE agent (%r) replied directly — resolving (Scenario A)",
                    thread.thread_id,
                    author,
                )
                return TierResult(
                    verdict=ResolutionVerdict.RESOLVE,
                    confidence="high",
                    tier_name=self.name,
                    explanation="Thread has been replied to by SWE agent.",
                )

        # Scenario B: session started after review + agent commented on PR.
        swe_session_started = getattr(context, "swe_session_started_after_review", False)
        swe_agent_commented = getattr(context, "swe_agent_commented_on_pr", False)
        if swe_session_started and swe_agent_commented:
            logger.debug(
                "Thread %s: SWE agent session started after review and agent replied on PR — resolving (Scenario B)",
                thread.thread_id,
            )
            return TierResult(
                verdict=ResolutionVerdict.RESOLVE,
                confidence="high",
                tier_name=self.name,
                explanation="SWE agent session started after this review and agent replied on PR.",
            )

        return None
