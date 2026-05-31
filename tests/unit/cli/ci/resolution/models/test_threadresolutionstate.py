"""Tests for ThreadResolutionState."""

from datetime import datetime, timedelta, timezone

from agentic_devtools.cli.ci.resolution.models import ResolutionVerdict, ThreadResolutionState


def test_to_dict_round_trip() -> None:
    state = ThreadResolutionState(
        thread_id="PRT_abc",
        verdict=ResolutionVerdict.TENTATIVE,
        tier_name="engine",
        confidence="low",
        timestamp="2026-01-01T00:00:00+00:00",
        iteration_count=2,
    )
    data = state.to_dict()
    restored = ThreadResolutionState.from_dict(data)
    assert restored.thread_id == "PRT_abc"
    assert restored.verdict == ResolutionVerdict.TENTATIVE
    assert restored.tier_name == "engine"
    assert restored.iteration_count == 2


def test_is_expired_by_iterations() -> None:
    state = ThreadResolutionState(
        thread_id="PRT_abc",
        verdict=ResolutionVerdict.TENTATIVE,
        tier_name="engine",
        confidence="low",
        iteration_count=5,
    )
    assert state.is_expired() is True


def test_is_expired_by_age() -> None:
    old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    state = ThreadResolutionState(
        thread_id="PRT_abc",
        verdict=ResolutionVerdict.TENTATIVE,
        tier_name="engine",
        confidence="low",
        timestamp=old_time,
        iteration_count=1,
    )
    assert state.is_expired() is True


def test_not_expired() -> None:
    state = ThreadResolutionState(
        thread_id="PRT_abc",
        verdict=ResolutionVerdict.TENTATIVE,
        tier_name="engine",
        confidence="low",
        iteration_count=2,
    )
    assert state.is_expired() is False


def test_increment_iteration() -> None:
    state = ThreadResolutionState(
        thread_id="PRT_abc",
        verdict=ResolutionVerdict.TENTATIVE,
        tier_name="engine",
        confidence="low",
        iteration_count=2,
    )
    state.increment_iteration()
    assert state.iteration_count == 3


def test_is_expired_returns_true_for_invalid_timestamp() -> None:
    state = ThreadResolutionState(
        thread_id="PRT_abc",
        verdict=ResolutionVerdict.TENTATIVE,
        tier_name="engine",
        confidence="low",
        timestamp="not-a-valid-datetime",
        iteration_count=1,
    )
    assert state.is_expired() is True
