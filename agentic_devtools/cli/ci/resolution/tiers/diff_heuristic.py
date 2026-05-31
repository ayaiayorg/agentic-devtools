"""Tier 3: Diff heuristic integration.

Resolves threads where the commented file/line range has been modified
in the diff between the review commit and HEAD. Wraps the existing
``check_lines_modified()`` function from ``evaluator/diff_heuristic.py``.
"""

from __future__ import annotations

import logging

from agentic_devtools.cli.ci.evaluator.diff_heuristic import check_lines_modified
from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, TierResult
from agentic_devtools.cli.ci.resolution.protocols import ResolutionContext, ReviewThread

logger = logging.getLogger(__name__)


class DiffHeuristicTier:
    """Tier 3: Resolve threads where commented lines were modified in the diff."""

    @property
    def name(self) -> str:
        return "diff_heuristic"

    def evaluate(self, thread: ReviewThread, context: ResolutionContext) -> TierResult | None:
        """Return RESOLVE if the thread's file/line range was modified in the diff."""
        # Skip PR-level comments (no file/line anchor)
        if thread.file_path is None or thread.start_line is None:
            return None

        logger.debug(
            "Thread %s: evaluating diff_heuristic tier (file=%s, lines=%s–%s)",
            thread.thread_id,
            thread.file_path,
            thread.start_line,
            thread.end_line or thread.start_line,
        )

        modified = check_lines_modified(
            diff_text=context.diff_text,
            path=thread.file_path,
            start_line=thread.start_line,
            end_line=thread.end_line,
        )

        if modified:
            return TierResult(
                verdict=ResolutionVerdict.RESOLVE,
                confidence="medium",
                tier_name=self.name,
                explanation=(
                    f"Lines {thread.start_line}–{thread.end_line or thread.start_line} "
                    f"in {thread.file_path} were modified since the review."
                ),
            )

        return None
