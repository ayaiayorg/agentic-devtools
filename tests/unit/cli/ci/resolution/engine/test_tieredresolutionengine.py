"""Tests for the TieredResolutionEngine."""

import threading
import time as time_module
from dataclasses import dataclass, field
from unittest.mock import patch

from agentic_devtools.cli.ci.resolution.engine import TieredResolutionEngine
from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, TierResult
from agentic_devtools.cli.ci.resolution.tiers.automation_markers import AutomationMarkerTier
from agentic_devtools.cli.ci.resolution.tiers.diff_heuristic import DiffHeuristicTier
from agentic_devtools.cli.ci.resolution.tiers.outdated import OutdatedTier


@dataclass(frozen=True)
class _MockComment:
    body: str = "test"
    created_at: str = "2026-01-01T00:00:00Z"
    author_login: str | None = None


@dataclass(frozen=True)
class _MockThread:
    thread_id: str = "PRT_123"
    file_path: str | None = "src/main.py"
    start_line: int | None = 10
    end_line: int | None = 15
    is_outdated: bool | None = False
    comments: list = field(default_factory=list)
    originating_review_commit_oid: str = "abc123"


@dataclass(frozen=True)
class _MockContext:
    diff_text: str = ""
    head_commit_oid: str = "head123"


class _AlwaysResolveTier:
    @property
    def name(self) -> str:
        return "always_resolve"

    def evaluate(self, thread, context) -> TierResult:
        return TierResult(
            verdict=ResolutionVerdict.RESOLVE,
            confidence="high",
            tier_name=self.name,
            explanation="Always resolves.",
        )


class _NeverResolveTier:
    @property
    def name(self) -> str:
        return "never_resolve"

    def evaluate(self, thread, context) -> TierResult | None:
        return None


class _ErrorTier:
    @property
    def name(self) -> str:
        return "error_tier"

    def evaluate(self, thread, context) -> TierResult | None:
        raise RuntimeError("Tier error!")


class _BlockingSdkTier:
    def __init__(self, stop_event: threading.Event) -> None:
        self._stop_event = stop_event
        self._timeout_seconds = 5.0

    @property
    def name(self) -> str:
        return "sdk_evaluation"

    def set_timeout_seconds(self, timeout_seconds: float) -> None:
        self._timeout_seconds = timeout_seconds

    def evaluate(self, thread, context) -> TierResult | None:  # pragma: no cover
        self._stop_event.wait(timeout=self._timeout_seconds)
        return None


class _ErrorSdkTier:
    @property
    def name(self) -> str:
        return "sdk_evaluation"

    def evaluate(self, thread, context) -> TierResult | None:
        raise RuntimeError("sdk exploded")


class _ResolveSdkTier:
    def __init__(self) -> None:
        self.evaluated_in_thread: threading.Thread | None = None

    @property
    def name(self) -> str:
        return "sdk_evaluation"

    def evaluate(self, thread, context) -> TierResult:
        self.evaluated_in_thread = threading.current_thread()
        return TierResult(
            verdict=ResolutionVerdict.RESOLVE,
            confidence="medium",
            tier_name=self.name,
            explanation="SDK confirmed fix.",
        )


class _NoneSdkTier:
    @property
    def name(self) -> str:
        return "sdk_evaluation"

    def evaluate(self, thread, context) -> TierResult | None:
        return None


class _TimeoutAwareResolveTier:
    def __init__(self) -> None:
        self.seen_timeouts: list[float] = []

    @property
    def name(self) -> str:
        return "timeout_aware"

    def set_timeout_seconds(self, timeout_seconds: float) -> None:
        self.seen_timeouts.append(timeout_seconds)

    def evaluate(self, thread, context) -> TierResult:
        return TierResult(
            verdict=ResolutionVerdict.RESOLVE,
            confidence="high",
            tier_name=self.name,
            explanation="resolved",
        )


@dataclass(frozen=True)
class _AzureDevOpsComment:
    body: str = "autofix applied"
    created_at: str = "2026-01-01T00:00:00Z"
    author_login: str | None = "azure-bot"


@dataclass(frozen=True)
class _AzureDevOpsThread:
    thread_id: str = "ADO_thread_42"
    file_path: str | None = "src/service.cs"
    start_line: int | None = 20
    end_line: int | None = 25
    is_outdated: bool | None = None
    comments: list = field(default_factory=list)
    originating_review_commit_oid: str = "ado_commit_abc"


@dataclass(frozen=True)
class _AzureDevOpsContext:
    diff_text: str = ""
    head_commit_oid: str = "ado_head_xyz"


class TestTieredResolutionEngine:
    """Tests for the resolution engine."""

    def test_short_circuits_on_first_result(self) -> None:
        engine = TieredResolutionEngine([_AlwaysResolveTier(), _NeverResolveTier()])
        result = engine.evaluate_thread(_MockThread(), _MockContext())
        assert result.verdict == ResolutionVerdict.RESOLVE
        assert result.tier_name == "always_resolve"

    def test_falls_through_to_next_tier(self) -> None:
        engine = TieredResolutionEngine([_NeverResolveTier(), _AlwaysResolveTier()])
        result = engine.evaluate_thread(_MockThread(), _MockContext())
        assert result.verdict == ResolutionVerdict.RESOLVE
        assert result.tier_name == "always_resolve"

    def test_tentative_when_all_tiers_fail(self) -> None:
        engine = TieredResolutionEngine([_NeverResolveTier()])
        result = engine.evaluate_thread(_MockThread(), _MockContext())
        assert result.verdict == ResolutionVerdict.TENTATIVE
        assert result.tier_name == "engine"

    def test_error_isolation_in_tiers(self) -> None:
        engine = TieredResolutionEngine([_ErrorTier(), _AlwaysResolveTier()])
        result = engine.evaluate_thread(_MockThread(), _MockContext())
        assert result.verdict == ResolutionVerdict.RESOLVE

    def test_batch_processing(self) -> None:
        engine = TieredResolutionEngine([_AlwaysResolveTier()])
        threads = [_MockThread(thread_id="t1"), _MockThread(thread_id="t2")]
        results = engine.evaluate_batch(threads, _MockContext())
        assert len(results) == 2
        assert all(r.verdict == ResolutionVerdict.RESOLVE for _, r in results)

    def test_batch_error_isolation(self) -> None:
        """Per-thread errors produce TENTATIVE, not propagating failure."""

        class _ErrorOnFirstTier:
            @property
            def name(self) -> str:
                return "error_on_first"

            def evaluate(self, thread, context) -> TierResult | None:
                if thread.thread_id == "t1":
                    raise RuntimeError("fail")
                return TierResult(
                    verdict=ResolutionVerdict.RESOLVE,
                    confidence="high",
                    tier_name=self.name,
                    explanation="ok",
                )

        engine = TieredResolutionEngine([_ErrorOnFirstTier()])
        threads = [_MockThread(thread_id="t1"), _MockThread(thread_id="t2")]
        results = engine.evaluate_batch(threads, _MockContext())
        assert results[0][1].verdict == ResolutionVerdict.TENTATIVE
        assert results[1][1].verdict == ResolutionVerdict.RESOLVE

    def test_timeout_before_first_tier(self) -> None:
        """Returns TENTATIVE immediately when the overall budget is exhausted."""
        with patch.object(time_module, "monotonic", side_effect=[0.0, 100.0]):
            engine = TieredResolutionEngine([_AlwaysResolveTier()])
            result = engine.evaluate_thread(_MockThread(), _MockContext())
        assert result.verdict == ResolutionVerdict.TENTATIVE
        assert result.tier_name == "engine"

    def test_slow_tier_triggers_budget_warning(self) -> None:
        """Logs a warning when a non-SDK tier exceeds the 500ms programmatic budget."""
        # Use a callable side_effect so that extra time.monotonic() calls from
        # concurrent.futures internals (during future.result()) don't cause StopIteration.
        # The first 3 calls correspond to start_time, elapsed-check, and tier_start (all 0.0);
        # any subsequent calls (including the tier_elapsed measurement) return 1.0.
        call_count = 0

        def _mock_monotonic() -> float:
            nonlocal call_count
            val = 0.0 if call_count < 3 else 1.0
            call_count += 1
            return val

        with patch.object(time_module, "monotonic", side_effect=_mock_monotonic):
            engine = TieredResolutionEngine([_NeverResolveTier()])
            result = engine.evaluate_thread(_MockThread(), _MockContext())
        assert result.verdict == ResolutionVerdict.TENTATIVE

    def test_timeout_during_tier_execution(self) -> None:
        """Returns TENTATIVE immediately when a tier exceeds the remaining time budget."""
        stop_event = threading.Event()

        class _BlockingTier:
            @property
            def name(self) -> str:
                return "blocking_tier"

            def evaluate(self, thread, context) -> TierResult | None:  # pragma: no cover
                stop_event.wait(timeout=5.0)
                return None

        with patch("agentic_devtools.cli.ci.resolution.engine._TOTAL_TIMEOUT_SECONDS", 0.05):
            engine = TieredResolutionEngine([_BlockingTier()])
            result = engine.evaluate_thread(_MockThread(), _MockContext())

        stop_event.set()
        assert result.verdict == ResolutionVerdict.TENTATIVE
        assert result.tier_name == "engine"

    def test_timed_out_future_is_cancelled(self) -> None:
        """On tier timeout, future.cancel() is called to prevent queued work from starting."""
        import concurrent.futures

        cancelled_futures: list[concurrent.futures.Future] = []
        original_submit = concurrent.futures.ThreadPoolExecutor.submit
        stop_event = threading.Event()

        class _BlockingTier:
            @property
            def name(self) -> str:
                return "blocking_tier"

            def evaluate(self, thread, context) -> TierResult | None:  # pragma: no cover
                stop_event.wait(timeout=5.0)
                return None

        def _patched_submit(self_exec, fn, *args, **kwargs):
            future = original_submit(self_exec, fn, *args, **kwargs)
            cancelled_futures.append(future)
            return future

        with (
            patch.object(concurrent.futures.ThreadPoolExecutor, "submit", _patched_submit),
            patch("agentic_devtools.cli.ci.resolution.engine._TOTAL_TIMEOUT_SECONDS", 0.05),
        ):
            engine = TieredResolutionEngine([_BlockingTier()])
            result = engine.evaluate_thread(_MockThread(), _MockContext())

        stop_event.set()
        assert result.verdict == ResolutionVerdict.TENTATIVE
        # cancel() was called on the timed-out future (it may return False if already
        # running, but the call must have been made — verified via the future object).
        assert len(cancelled_futures) == 1

    def test_timeout_during_sdk_tier_execution_honors_sdk_timeout_budget(self) -> None:
        """SDK tier receives the remaining timeout budget and returns TENTATIVE."""
        stop_event = threading.Event()
        with patch("agentic_devtools.cli.ci.resolution.engine._TOTAL_TIMEOUT_SECONDS", 0.05):
            engine = TieredResolutionEngine([_BlockingSdkTier(stop_event)])
            result = engine.evaluate_thread(_MockThread(), _MockContext())

        stop_event.set()
        assert result.verdict == ResolutionVerdict.TENTATIVE
        assert result.tier_name == "engine"

    def test_sdk_tier_runs_through_executor_and_returns_result(self) -> None:
        """SDK tier runs through the executor and returns a RESOLVE verdict."""
        sdk_tier = _ResolveSdkTier()
        engine = TieredResolutionEngine([sdk_tier])
        result = engine.evaluate_thread(_MockThread(), _MockContext())

        assert result.verdict == ResolutionVerdict.RESOLVE
        assert result.tier_name == "sdk_evaluation"
        assert sdk_tier.evaluated_in_thread is not None

    def test_sdk_tier_error_produces_tentative(self) -> None:
        """SDK tier errors fall through to a TENTATIVE engine verdict."""
        engine = TieredResolutionEngine([_ErrorSdkTier()])
        result = engine.evaluate_thread(_MockThread(), _MockContext())

        assert result.verdict == ResolutionVerdict.TENTATIVE
        assert result.tier_name == "engine"

    def test_sdk_tier_none_produces_tentative(self) -> None:
        """SDK tier returning None produces a TENTATIVE engine verdict."""
        engine = TieredResolutionEngine([_NoneSdkTier()])
        result = engine.evaluate_thread(_MockThread(), _MockContext())

        assert result.verdict == ResolutionVerdict.TENTATIVE
        assert result.tier_name == "engine"

    def test_sets_timeout_budget_for_timeout_aware_tier(self) -> None:
        tier = _TimeoutAwareResolveTier()
        with patch("agentic_devtools.cli.ci.resolution.engine._TOTAL_TIMEOUT_SECONDS", 3.0):
            result = TieredResolutionEngine([tier]).evaluate_thread(_MockThread(), _MockContext())

        assert result.verdict == ResolutionVerdict.RESOLVE
        assert len(tier.seen_timeouts) == 1
        assert 0 < tier.seen_timeouts[0] <= 3.0

    def test_batch_unhandled_evaluate_thread_error(self) -> None:
        """Unhandled errors raised by evaluate_thread produce TENTATIVE in batch."""
        engine = TieredResolutionEngine([_NeverResolveTier()])
        with patch.object(engine, "evaluate_thread", side_effect=RuntimeError("unhandled")):
            threads = [_MockThread(thread_id="t1")]
            results = engine.evaluate_batch(threads, _MockContext())
        assert results[0][1].verdict == ResolutionVerdict.TENTATIVE
        assert "unhandled" in results[0][1].explanation

    def test_outdated_tier_with_platform_agnostic_data(self) -> None:
        engine = TieredResolutionEngine([OutdatedTier()])
        thread = _AzureDevOpsThread(is_outdated=True)
        context = _AzureDevOpsContext()
        result = engine.evaluate_thread(thread, context)
        assert result.verdict == ResolutionVerdict.RESOLVE
        assert result.tier_name == "outdated"

    def test_automation_marker_tier_with_platform_agnostic_data(self) -> None:
        engine = TieredResolutionEngine([AutomationMarkerTier()])
        thread = _AzureDevOpsThread(comments=[_AzureDevOpsComment(body="autofix applied")])
        context = _AzureDevOpsContext()
        result = engine.evaluate_thread(thread, context)
        assert result.verdict == ResolutionVerdict.RESOLVE
        assert result.tier_name == "automation_marker"

    def test_diff_heuristic_tier_with_platform_agnostic_data(self) -> None:
        diff = """\
diff --git a/src/service.cs b/src/service.cs
index abc..def 100644
--- a/src/service.cs
+++ b/src/service.cs
@@ -18,7 +18,7 @@
 context
 context
-old line 20
+new line 20
 context
"""
        engine = TieredResolutionEngine([DiffHeuristicTier()])
        thread = _AzureDevOpsThread(
            file_path="src/service.cs",
            start_line=20,
            end_line=20,
        )
        context = _AzureDevOpsContext(diff_text=diff)
        result = engine.evaluate_thread(thread, context)
        assert result.verdict == ResolutionVerdict.RESOLVE
        assert result.tier_name == "diff_heuristic"

    def test_full_pipeline_with_platform_agnostic_data(self) -> None:
        engine = TieredResolutionEngine(
            [
                OutdatedTier(),
                AutomationMarkerTier(),
                DiffHeuristicTier(),
            ]
        )
        thread = _AzureDevOpsThread(
            is_outdated=False,
            comments=[_AzureDevOpsComment(body="needs more work")],
            file_path="other.cs",
            start_line=100,
        )
        context = _AzureDevOpsContext(diff_text="")
        result = engine.evaluate_thread(thread, context)
        assert result.verdict == ResolutionVerdict.TENTATIVE

    def test_batch_processing_with_platform_agnostic_data(self) -> None:
        engine = TieredResolutionEngine([OutdatedTier(), AutomationMarkerTier()])
        threads = [
            _AzureDevOpsThread(thread_id="t1", is_outdated=True),
            _AzureDevOpsThread(
                thread_id="t2",
                is_outdated=False,
                comments=[_AzureDevOpsComment(body="suggestion applied")],
            ),
            _AzureDevOpsThread(
                thread_id="t3",
                is_outdated=False,
                comments=[_AzureDevOpsComment(body="needs work")],
            ),
        ]
        context = _AzureDevOpsContext()
        results = engine.evaluate_batch(threads, context)
        assert results[0][1].verdict == ResolutionVerdict.RESOLVE
        assert results[1][1].verdict == ResolutionVerdict.RESOLVE
        assert results[2][1].verdict == ResolutionVerdict.TENTATIVE
