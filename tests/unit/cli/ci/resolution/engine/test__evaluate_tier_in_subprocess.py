"""Tests for _evaluate_tier_in_subprocess."""

import multiprocessing as _mp
from dataclasses import dataclass, field
from unittest.mock import patch

from agentic_devtools.cli.ci.resolution.engine import (
    _evaluate_tier_in_subprocess,
)
from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, TierResult


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


class _ErrorSdkTier:
    @property
    def name(self) -> str:
        return "sdk_evaluation"

    def evaluate(self, thread, context) -> TierResult | None:
        raise RuntimeError("sdk exploded")


def test_evaluate_tier_in_subprocess_returns_result_payload() -> None:
    result, timed_out, error_raised = _evaluate_tier_in_subprocess(
        _AlwaysResolveTier(),
        _MockThread(),
        _MockContext(),
        timeout_seconds=1.0,
    )
    assert timed_out is False
    assert error_raised is None
    assert result is not None
    assert result.verdict == ResolutionVerdict.RESOLVE


def test_evaluate_tier_in_subprocess_converts_error_payload_to_runtime_error() -> None:
    result, timed_out, error_raised = _evaluate_tier_in_subprocess(
        _ErrorSdkTier(),
        _MockThread(),
        _MockContext(),
        timeout_seconds=1.0,
    )
    assert result is None
    assert timed_out is False
    assert isinstance(error_raised, RuntimeError)
    assert "sdk exploded" in str(error_raised)


def test_evaluate_tier_in_subprocess_handles_empty_queue_with_clean_exit() -> None:
    def _worker_without_queue_payload(_tier, _thread, _context, _result_queue) -> None:
        return None

    with patch(
        "agentic_devtools.cli.ci.resolution.engine._run_tier_in_subprocess",
        _worker_without_queue_payload,
    ):
        result, timed_out, error_raised = _evaluate_tier_in_subprocess(
            _AlwaysResolveTier(),
            _MockThread(),
            _MockContext(),
            timeout_seconds=1.0,
        )

    assert result is None
    assert timed_out is False
    assert error_raised is None


def test_evaluate_tier_in_subprocess_handles_empty_queue_with_crash_exit() -> None:
    def _worker_exits_nonzero(_tier, _thread, _context, _result_queue) -> None:
        raise RuntimeError("boom")

    with patch(
        "agentic_devtools.cli.ci.resolution.engine._run_tier_in_subprocess",
        _worker_exits_nonzero,
    ):
        result, timed_out, error_raised = _evaluate_tier_in_subprocess(
            _AlwaysResolveTier(),
            _MockThread(),
            _MockContext(),
            timeout_seconds=1.0,
        )

    assert result is None
    assert timed_out is False
    assert isinstance(error_raised, RuntimeError)
    assert "tier process exited with code" in str(error_raised)


def test_evaluate_tier_in_subprocess_gracefully_degrades_when_fork_unavailable() -> None:
    """Returns error tuple instead of crashing when 'fork' context is unavailable."""
    with patch.object(_mp, "get_context", side_effect=ValueError("fork not available")):
        result, timed_out, error_raised = _evaluate_tier_in_subprocess(
            _AlwaysResolveTier(),
            _MockThread(),
            _MockContext(),
            timeout_seconds=1.0,
        )

    assert result is None
    assert timed_out is False
    assert isinstance(error_raised, ValueError)
    assert "fork not available" in str(error_raised)
