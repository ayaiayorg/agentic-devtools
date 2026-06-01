"""Tiered resolution engine orchestrator.

Iterates through evaluation tiers in strict order, short-circuiting on the
first non-None result. If all tiers fail to produce a verdict, returns
TENTATIVE.
"""

from __future__ import annotations

import concurrent.futures
import logging
import time
from collections.abc import Sequence

from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, TierResult
from agentic_devtools.cli.ci.resolution.protocols import EvaluationTier, ResolutionContext, ReviewThread

logger = logging.getLogger(__name__)

# Budget warnings
_PROGRAMMATIC_TIER_BUDGET_MS = 500
_TOTAL_TIMEOUT_SECONDS = 45.0


class TieredResolutionEngine:
    """Orchestrates tiered thread resolution evaluation.

    Evaluates threads through a sequence of tiers in strict order.
    Short-circuits on the first non-None result. If all tiers produce
    None, returns a TENTATIVE verdict.

    Args:
        tiers: Ordered list of evaluation tiers to apply.
    """

    def __init__(self, tiers: list[EvaluationTier]) -> None:
        self._tiers = tiers

    def evaluate_thread(self, thread: ReviewThread, context: ResolutionContext) -> TierResult:
        """Evaluate a single thread through all tiers.

        Returns:
            TierResult with the verdict from the first matching tier,
            or a TENTATIVE result if no tier could determine a verdict.

        A single ThreadPoolExecutor (max_workers=1) is used for all tiers so
        that at most one background worker is ever in flight. On timeout the future
        is cancelled (no-op if already running, prevents any queued work from
        starting). All tiers, including the SDK tier, run through the executor so
        the overall budget is enforced uniformly.
        """
        start_time = time.monotonic()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            for tier in self._tiers:
                elapsed = time.monotonic() - start_time
                remaining = _TOTAL_TIMEOUT_SECONDS - elapsed
                if remaining <= 0:
                    logger.warning(
                        "Thread %s: evaluation timeout (%.1fs) — marking TENTATIVE",
                        thread.thread_id,
                        elapsed,
                    )
                    break

                tier_start = time.monotonic()
                timed_out = False
                result: TierResult | None = None
                error_raised: Exception | None = None

                set_timeout_seconds = getattr(tier, "set_timeout_seconds", None)
                if callable(set_timeout_seconds):
                    set_timeout_seconds(remaining)

                future = executor.submit(tier.evaluate, thread, context)
                try:
                    result = future.result(timeout=remaining)
                except concurrent.futures.TimeoutError:
                    future.cancel()
                    timed_out = True
                except Exception as exc:
                    error_raised = exc

                if timed_out:
                    logger.warning(
                        "Thread %s: tier %s timed out after %.1fs — marking TENTATIVE",
                        thread.thread_id,
                        tier.name,
                        remaining,
                    )
                    break

                if error_raised is not None:
                    logger.error(
                        "Thread %s: tier %s raised %s — skipping",
                        thread.thread_id,
                        tier.name,
                        error_raised,
                    )
                    continue

                tier_elapsed_ms = (time.monotonic() - tier_start) * 1000
                if tier_elapsed_ms > _PROGRAMMATIC_TIER_BUDGET_MS and tier.name != "sdk_evaluation":
                    logger.warning(
                        "Thread %s: tier %s took %.0fms (budget: %dms)",
                        thread.thread_id,
                        tier.name,
                        tier_elapsed_ms,
                        _PROGRAMMATIC_TIER_BUDGET_MS,
                    )

                if result is not None:
                    logger.debug(
                        "Thread %s: tier %s → %s (confidence=%s)",
                        thread.thread_id,
                        tier.name,
                        result.verdict.value,
                        result.confidence,
                    )
                    return result

        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        # All tiers returned None — tentative verdict
        return TierResult(
            verdict=ResolutionVerdict.TENTATIVE,
            confidence="low",
            tier_name="engine",
            explanation="No tier could determine a verdict — marking as tentative.",
        )

    def evaluate_batch(
        self, threads: Sequence[ReviewThread], context: ResolutionContext
    ) -> list[tuple[ReviewThread, TierResult]]:
        """Evaluate multiple threads with per-thread error isolation.

        Returns:
            List of (thread, result) tuples. Failed threads get TENTATIVE.
        """
        results: list[tuple[ReviewThread, TierResult]] = []

        for thread in threads:
            try:
                result = self.evaluate_thread(thread, context)
            except Exception as exc:
                logger.error("Thread %s: unhandled error — %s", thread.thread_id, exc)
                result = TierResult(
                    verdict=ResolutionVerdict.TENTATIVE,
                    confidence="low",
                    tier_name="engine",
                    explanation=f"Evaluation failed: {exc}",
                )
            results.append((thread, result))

        return results
